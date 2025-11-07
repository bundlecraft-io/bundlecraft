#!/usr/bin/env python3
"""
fetch.py
First stage of the BundleCraft pipeline: securely fetch and stage certificate sources.

Design choices per ADR-0002 and user guidance:
 - No persistent caching; fetched artifacts are staged under cert_sources/staged/<source_name>/fetch/<name>/
 - Staging directory is cleaned at the start of each fetch run
 - Only trusted origins: HTTPS/file URLs supported; optional content SHA256 pinning
 - Staged files are treated the same as local sources by the build stage
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from bundlecraft.fetchers.api import fetch_api
from bundlecraft.fetchers.azure_blob import fetch_azure_blob
from bundlecraft.fetchers.gcs import fetch_gcs
from bundlecraft.fetchers.http import fetch_url
from bundlecraft.fetchers.mozilla import fetch_mozilla
from bundlecraft.fetchers.s3 import fetch_s3
from bundlecraft.fetchers.vault import fetch_vault
from bundlecraft.helpers.config_schema import validate_source_config
from bundlecraft.helpers.exit_codes import ExitCode
from bundlecraft.helpers.ui import print_banner
from bundlecraft.helpers.utils import ensure_dir, load_yaml, sha256_file

CURRENT_DIR = Path(__file__).resolve().parent

# Setup logger
logger = logging.getLogger("bundlecraft.fetch")
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
# Avoid duplicate log lines by preventing propagation to the root logger
logger.propagate = False


# Names that are reserved for internal use within the staging directory
_RESERVED_STAGING_NAMES: set[str] = {"include"}


def _validate_source_and_fetch_names(cfg: dict[str, Any]) -> None:
    """Validate that local repo names and fetch names are unique and non-reserved.

    Rules:
      - repo: must be a list of objects with unique 'name' values
      - fetch: if 'name' is provided explicitly, names must be unique
      - No repo/fetch name may use a reserved name (e.g., 'include')
      - No repo name may conflict with a fetch name
    Raises click.ClickException on violation.
    """
    repos = cfg.get("repo") or []
    fetches = cfg.get("fetch") or []

    repo_names: list[str] = []
    if repos:
        if not isinstance(repos, list):
            raise click.ClickException("Config key 'repo' must be a list of sources")
        for idx, r in enumerate(repos, start=1):
            if not isinstance(r, dict):
                raise click.ClickException("Each 'repo' entry must be an object with a 'name'")
            name = (r.get("name") or "").strip()
            if not name:
                raise click.ClickException(f"Local repo entry #{idx} is missing required 'name'")
            if name in _RESERVED_STAGING_NAMES:
                raise click.ClickException(
                    f"Local repo name '{name}' is reserved. Choose a different name."
                )
            if name in repo_names:
                raise click.ClickException(f"Duplicate local repo name: '{name}'")
            repo_names.append(name)

    fetch_names_explicit: list[str] = []
    if fetches:
        if not isinstance(fetches, list):
            raise click.ClickException("Config key 'fetch' must be a list of sources")
    for _idx, f in enumerate(fetches, start=1):
        if not isinstance(f, dict):
            raise click.ClickException("Each 'fetch' entry must be an object")
        name = (f.get("name") or "").strip()
        if not name:
            # Auto-generated names like fetched-1 are unique by index; ignore for duplication check
            continue
        if name in _RESERVED_STAGING_NAMES:
            raise click.ClickException(f"Fetch name '{name}' is reserved. Choose a different name.")
        if name in fetch_names_explicit:
            raise click.ClickException(f"Duplicate fetch name: '{name}'")
        fetch_names_explicit.append(name)

    # Cross-conflict between repo names and fetch names
    conflicts = set(repo_names).intersection(set(fetch_names_explicit))
    if conflicts:
        raise click.ClickException(
            "Name conflict between local 'repo' and 'fetch' entries: "
            + ", ".join(sorted(conflicts))
        )


def _clean_dir(path: Path) -> None:
    if path.exists():
        for p in sorted(path.rglob("*"), reverse=True):
            try:
                if p.is_file() or p.is_symlink():
                    p.unlink(missing_ok=True)
                elif p.is_dir():
                    p.rmdir()
            except Exception:
                # Best-effort cleanup; continue
                pass


def _write_provenance(dir_path: Path, records: list[dict[str, Any]]) -> None:
    prov = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "items": records,
    }
    (dir_path / "provenance.fetch.json").write_text(
        json.dumps(prov, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _fetch_from_config(
    fetch_cfg: list[dict[str, Any]],
    dest_dir: Path,
    root: Path,
    verbose: bool = False,
    defaults: dict | None = None,
) -> list[Path]:
    outputs: list[Path] = []
    provenance: list[dict[str, Any]] = []

    for idx, src in enumerate(fetch_cfg, start=1):
        ftype = (src.get("type") or "url").lower()
        name = src.get("name") or f"fetched-{idx}"
        verify = src.get("verify") or {}

        # Extract retry/timeout configuration from source
        timeout = src.get("timeout")
        retries = src.get("retries")
        backoff_factor = src.get("backoff_factor")
        retry_on_status = src.get("retry_on_status")

        logger.info(f"[Fetch {idx}/{len(fetch_cfg)}] Type: {ftype}, Name: {name}")
        if verbose:
            logger.debug(f"  Full config: {json.dumps(src, indent=2)}")

        try:
            if ftype == "url":
                url = src.get("url")
                if not url:
                    raise click.ClickException("Fetch source missing 'url'")
                logger.info(f"  Fetching from URL: {url}")
                if verbose and verify:
                    logger.debug(f"  Verification config: {json.dumps(verify, indent=2)}")
                out_path = fetch_url(
                    url,
                    dest_dir,
                    name=name,
                    verify=verify,
                    root=root,
                    timeout=timeout,
                    retries=retries,
                    backoff_factor=backoff_factor,
                    retry_on_status=retry_on_status,
                    defaults=defaults,
                )
            elif ftype == "api":
                endpoint = src.get("endpoint") or src.get("url")
                if not endpoint:
                    raise click.ClickException("API fetch source requires 'endpoint' (or 'url')")
                provider = src.get("provider")
                token_ref = src.get("token_ref")
                headers = (verify or {}).get("headers") if isinstance(verify, dict) else None
                logger.info(f"  Fetching from API: {endpoint}")
                logger.info(f"    Provider: {provider or 'generic'}")
                if verbose:
                    logger.debug(f"    Token ref: {token_ref}")
                    if headers:
                        logger.debug(f"    Custom headers: {list(headers.keys())}")
                out_path = fetch_api(
                    endpoint,
                    dest_dir,
                    name=name,
                    provider=provider,
                    token_ref=token_ref,
                    headers=headers,
                    verify=verify if isinstance(verify, dict) else None,
                    timeout=timeout,
                    retries=retries,
                    backoff_factor=backoff_factor,
                    retry_on_status=retry_on_status,
                    defaults=defaults,
                )
            elif ftype == "mozilla":
                logger.info("  Fetching Mozilla CA Bundle from curl.se")
                if verbose and verify:
                    logger.debug(f"  Verification config: {json.dumps(verify, indent=2)}")
                out_path = fetch_mozilla(
                    dest_dir,
                    name=name,
                    verify=verify,
                    root=root,
                    timeout=timeout,
                    retries=retries,
                    backoff_factor=backoff_factor,
                    retry_on_status=retry_on_status,
                    defaults=defaults,
                )
            elif ftype == "vault":
                mount_point = (
                    src.get("mount_point") or src.get("mount") or src.get("engine") or "secret"
                )
                path = src.get("path")
                if not path:
                    raise click.ClickException("Vault fetch source requires 'path'")
                pem_field = src.get("pem_field") or "pem"
                addr = src.get("addr")  # fallback to VAULT_ADDR if not provided
                token_ref = src.get("token_ref")  # fallback to VAULT_TOKEN
                namespace = src.get("namespace")
                logger.info("  Fetching from Vault:")
                logger.info(f"    Address: {addr or 'from VAULT_ADDR env'}")
                logger.info(f"    Mount: {mount_point}, Path: {path}")
                logger.info(f"    Field: {pem_field}")
                if verbose:
                    logger.debug(f"    Namespace: {namespace or 'default'}")
                    logger.debug(f"    Token ref: {token_ref or 'from VAULT_TOKEN env'}")
                out_path = fetch_vault(
                    dest_dir,
                    name=name,
                    mount_point=mount_point,
                    path=path,
                    pem_field=pem_field,
                    addr=addr,
                    token_ref=token_ref,
                    namespace=namespace,
                    verify=verify if isinstance(verify, dict) else None,
                )
            elif ftype == "gcs":
                bucket = src.get("bucket")
                if not bucket:
                    raise click.ClickException("GCS fetch source requires 'bucket'")
                object_path = src.get("object_path") or src.get("object") or src.get("path")
                if not object_path:
                    raise click.ClickException(
                        "GCS fetch source requires 'object_path' (or 'object')"
                    )
                credentials_file = src.get("credentials_file")
                project = src.get("project")
                logger.info("  Fetching from Google Cloud Storage:")
                logger.info(f"    Bucket: {bucket}")
                logger.info(f"    Object: {object_path}")
                if verbose:
                    logger.debug(f"    Project: {project or 'default'}")
                    logger.debug(
                        f"    Credentials: {credentials_file or 'from GOOGLE_APPLICATION_CREDENTIALS env or ADC'}"
                    )
                out_path = fetch_gcs(
                    dest_dir,
                    name=name,
                    bucket=bucket,
                    object_path=object_path,
                    credentials_file=credentials_file,
                    project=project,
                    verify=verify if isinstance(verify, dict) else None,
                    timeout=timeout,
                    retries=retries,
                    backoff_factor=backoff_factor,
                    retry_on_status=retry_on_status,
                    defaults=defaults,
                )
            elif ftype == "azure_blob":
                container = src.get("container")
                blob_name = src.get("blob_name")
                if not container:
                    raise click.ClickException("Azure Blob fetch source requires 'container'")
                if not blob_name:
                    raise click.ClickException("Azure Blob fetch source requires 'blob_name'")
                account_name = src.get("account_name")
                connection_string_ref = src.get("connection_string_ref")
                account_key_ref = src.get("account_key_ref")
                sas_token_ref = src.get("sas_token_ref")
                use_managed_identity = src.get("use_managed_identity", False)
                logger.info("  Fetching from Azure Blob Storage:")
                logger.info(f"    Container: {container}")
                logger.info(f"    Blob: {blob_name}")
                if account_name:
                    logger.info(f"    Account: {account_name}")
                if verbose:
                    auth_method = (
                        "connection_string"
                        if connection_string_ref
                        else (
                            "account_key"
                            if account_key_ref
                            else (
                                "sas_token"
                                if sas_token_ref
                                else (
                                    "managed_identity"
                                    if use_managed_identity
                                    else "default_credential"
                                )
                            )
                        )
                    )
                    logger.debug(f"    Auth method: {auth_method}")
                out_path = fetch_azure_blob(
                    dest_dir,
                    name=name,
                    container=container,
                    blob_name=blob_name,
                    account_name=account_name,
                    connection_string_ref=connection_string_ref,
                    account_key_ref=account_key_ref,
                    sas_token_ref=sas_token_ref,
                    use_managed_identity=use_managed_identity,
                    verify=verify if isinstance(verify, dict) else None,
                    timeout=timeout,
                    retries=retries,
                    backoff_factor=backoff_factor,
                    retry_on_status=retry_on_status,
                    defaults=defaults,
                )
            elif ftype == "s3":
                # S3 fetcher supports both s3:// URLs and explicit bucket/key parameters
                url_param = src.get("url")
                bucket = src.get("bucket")
                key_param = src.get("key")
                region = src.get("region")
                endpoint_url = src.get("endpoint_url")

                if url_param:
                    logger.info(f"  Fetching from S3: {url_param}")
                elif bucket and key_param:
                    logger.info(f"  Fetching from S3: s3://{bucket}/{key_param}")
                    if region:
                        logger.info(f"    Region: {region}")
                else:
                    raise click.ClickException(
                        "S3 fetch requires either 'url' (s3://bucket/key) or both 'bucket' and 'key'"
                    )

                if verbose:
                    if endpoint_url:
                        logger.debug(f"    Custom endpoint: {endpoint_url}")
                    logger.debug("    Using AWS credential chain for authentication")

                out_path = fetch_s3(
                    dest_dir,
                    name=name,
                    url=url_param,
                    bucket=bucket,
                    key=key_param,
                    region=region,
                    endpoint_url=endpoint_url,
                    verify=verify if isinstance(verify, dict) else None,
                    timeout=timeout,
                    retries=retries,
                    backoff_factor=backoff_factor,
                    retry_on_status=retry_on_status,
                    defaults=defaults,
                )
            else:
                raise click.ClickException(f"Unsupported fetch type: {ftype}")

            actual_sha = sha256_file(out_path)
            logger.info(f"  ✓ Fetched successfully: {out_path.name}")
            logger.info(f"    SHA256: {actual_sha}")

            if "sha256" in verify:
                expected_sha256 = str(verify.get("sha256"))
                if actual_sha.lower() != expected_sha256.lower():
                    out_path.unlink(missing_ok=True)
                    logger.error(f"  ✗ SHA256 mismatch for {name}:")
                    logger.error(f"    Expected: {expected_sha256}")
                    logger.error(f"    Got:      {actual_sha}")
                    raise click.ClickException(
                        f"SHA256 mismatch for {name}: expected {expected_sha256}, got {actual_sha}"
                    )
                logger.info("  ✓ SHA256 verification passed")

            outputs.append(out_path)
            provenance.append(
                {
                    "name": name,
                    "origin": src,
                    "staged_path": str(out_path.relative_to(root)),
                    "sha256": actual_sha,
                }
            )
        except click.ClickException:
            raise
        except Exception as e:
            logger.error(f"  ✗ Fetch failed for {name}: {e}")
            if verbose:
                import traceback

                logger.error(traceback.format_exc())
            raise click.ClickException(f"Fetch failed for {name}: {e}") from e

    _write_provenance(dest_dir, provenance)
    return outputs


def run_fetch(
    env: str,
    bundle: str,
    workspace_root: Path,
    no_clean: bool = False,
    offline: bool = False,
    verbose: bool = False,
) -> list[Path]:
    """Programmatic entrypoint to fetch-and-stage.

    Args:
        env: Environment config file identifier (e.g., 'dev' for config/envs/dev.yaml)

    Returns list of staged file paths. No-op (empty list) if no fetch section.
    Raises ClickException on validation errors.
    """
    root = workspace_root.resolve()
    config_dir = root / "config"
    sources_dir = root / "cert_sources"

    # Ensure basic structure exists
    ensure_dir(sources_dir)

    # Load config
    cfg_path = config_dir / "envs" / f"{env}.yaml"
    env_cfg = load_yaml(cfg_path, required=True)
    env_name = env_cfg.get("name") or env
    logger.info(f"Loading config for environment '{env_name}', bundle '{bundle}'")
    bundle_cfg = load_yaml(
        config_dir / "bundles" / f"{bundle}.yaml", required=True, validate=validate_source_config
    )
    fetch_cfg = bundle_cfg.get("fetch") or []
    if not isinstance(fetch_cfg, list):
        raise click.ClickException("Config key 'fetch' must be a list of sources")
    if not fetch_cfg:
        return []

    logger.info(f"Found {len(fetch_cfg)} fetch source(s)")
    dest_dir = sources_dir / "fetched" / env / bundle
    ensure_dir(dest_dir)
    if not no_clean:
        logger.info(f"Cleaning staging directory: {dest_dir}")
        _clean_dir(dest_dir)
        ensure_dir(dest_dir)

    if offline:
        # In offline mode, do not perform network calls. If any fetch entries exist, fail.
        raise click.ClickException("Offline mode is enabled but fetch entries are present.")
    outputs = _fetch_from_config(fetch_cfg, dest_dir, root, verbose=verbose)
    return outputs


def _stage_local_includes(
    cfg: dict[str, Any], staging_root: Path, root: Path, verbose: bool, dry_run: bool = False
) -> list[Path]:
    """Stage local sources into named subdirectories.

    Supports two schemas:
      1) New: repo: - name: <name>, include: [...], exclude: [...]
         Staged under: <staging_root>/<name>/
      2) Legacy: include: [...], exclude: [...]
         Staged under: <staging_root>/include/
    """

    staged: list[Path] = []

    # Validate names against fetch entries to avoid conflicts
    _validate_source_and_fetch_names(cfg)

    # New schema: named repos
    repos = cfg.get("repo") or []
    if repos:
        logger.info("[Local] Copying named repos ...")
        for r in repos:
            name = r.get("name")
            include_items = r.get("include") or []
            exclude_items = set(r.get("exclude") or [])
            if not include_items:
                if verbose:
                    logger.debug(f"  Repo '{name}' has no include items; skipping")
                continue
            subdir = staging_root / name
            if not dry_run:
                ensure_dir(subdir)
            for idx, item in enumerate(include_items, start=1):
                # Back-compat: allow include items to be plain strings (paths)
                if isinstance(item, str):
                    p = (root / item).resolve()
                    if p.is_dir():
                        for f in sorted(p.rglob("*.pem")):
                            rel_str = str(f.relative_to(root)).replace("\\", "/")
                            if rel_str in exclude_items:
                                if verbose:
                                    logger.debug(f"  Skipped (excluded): {rel_str}")
                                continue
                            out = subdir / f.name
                            if dry_run:
                                logger.info(f"  [{name}] [dry-run] Would copy: {rel_str} -> {out}")
                            else:
                                out.write_bytes(f.read_bytes())
                                staged.append(out)
                                logger.info(f"  [{name}] Copied: {rel_str} -> {out}")
                    elif p.is_file():
                        rel_str = str(p.relative_to(root)).replace("\\", "/")
                        if rel_str in exclude_items:
                            if verbose:
                                logger.debug(f"  Skipped (excluded): {rel_str}")
                            continue
                        out = subdir / p.name
                        if dry_run:
                            logger.info(f"  [{name}] [dry-run] Would copy: {rel_str} -> {out}")
                        else:
                            out.write_bytes(p.read_bytes())
                            staged.append(out)
                            logger.info(f"  [{name}] Copied: {rel_str} -> {out}")
                    else:
                        logger.warning(f"  [{name}] Include path not found: {item}")
                    continue

                if isinstance(item, dict):
                    # Dictionary form supports either 'path' or 'inline' (inline PEM)
                    if "path" in item and item["path"]:
                        p = root / str(item["path"])
                        p = p.resolve()
                        if p.is_dir():
                            for f in sorted(p.rglob("*.pem")):
                                rel_str = str(f.relative_to(root)).replace("\\", "/")
                                if rel_str in exclude_items:
                                    if verbose:
                                        logger.debug(f"  Skipped (excluded): {rel_str}")
                                    continue
                                out = subdir / f.name
                                if dry_run:
                                    logger.info(
                                        f"  [{name}] [dry-run] Would copy: {rel_str} -> {out}"
                                    )
                                else:
                                    out.write_bytes(f.read_bytes())
                                    staged.append(out)
                                    logger.info(f"  [{name}] Copied: {rel_str} -> {out}")
                        elif p.is_file():
                            rel_str = str(p.relative_to(root)).replace("\\", "/")
                            if rel_str in exclude_items:
                                if verbose:
                                    logger.debug(f"  Skipped (excluded): {rel_str}")
                                continue
                            out = subdir / p.name
                            if dry_run:
                                logger.info(f"  [{name}] [dry-run] Would copy: {rel_str} -> {out}")
                            else:
                                out.write_bytes(p.read_bytes())
                                staged.append(out)
                                logger.info(f"  [{name}] Copied: {rel_str} -> {out}")
                        else:
                            logger.warning(f"  [{name}] Include path not found: {item.get('path')}")
                        continue

                    if "inline" in item and item["inline"]:
                        import textwrap

                        pem_text = textwrap.dedent(str(item["inline"]))
                        pem_text = pem_text.strip()
                        # Filename can be specified or auto-generated
                        fname = item.get("name") or f"inline-{idx}.pem"
                        out = subdir / fname
                        # Ensure newline termination
                        if not pem_text.endswith("\n"):
                            pem_text += "\n"
                        if dry_run:
                            logger.info(f"  [{name}] [dry-run] Would write inline PEM -> {out}")
                        else:
                            out.write_text(pem_text, encoding="utf-8")
                            staged.append(out)
                            logger.info(f"  [{name}] Wrote inline PEM -> {out}")
                        continue

                    logger.warning(
                        f"  [{name}] Unrecognized include item (expected 'path' or 'inline'): {item}"
                    )
                    continue

                logger.warning(f"  [{name}] Unsupported include item type: {type(item)}")

    # Legacy schema: flat include/exclude
    include_items_legacy = cfg.get("include") or []
    if include_items_legacy:
        exclude_items_legacy = set(cfg.get("exclude") or [])
        include_dir = staging_root / "include"
        if not dry_run:
            ensure_dir(include_dir)
        logger.info("[Local] Copying legacy includes ...")
        for item in include_items_legacy:
            p = (root / item).resolve()
            if p.is_dir():
                for f in sorted(p.rglob("*.pem")):
                    rel_str = str(f.relative_to(root)).replace("\\", "/")
                    if rel_str in exclude_items_legacy:
                        if verbose:
                            logger.debug(f"  Skipped (excluded): {rel_str}")
                        continue
                    out = include_dir / f.name
                    if dry_run:
                        logger.info(f"  [dry-run] Would copy: {rel_str} -> {out}")
                    else:
                        out.write_bytes(f.read_bytes())
                        staged.append(out)
                        logger.info(f"  Copied: {rel_str} -> {out}")
            elif p.is_file():
                rel_str = str(p.relative_to(root)).replace("\\", "/")
                if rel_str in exclude_items_legacy:
                    if verbose:
                        logger.debug(f"  Skipped (excluded): {rel_str}")
                    continue
                out = include_dir / p.name
                if dry_run:
                    logger.info(f"  [dry-run] Would copy: {rel_str} -> {out}")
                else:
                    out.write_bytes(p.read_bytes())
                    staged.append(out)
                    logger.info(f"  Copied: {rel_str} -> {out}")
            else:
                logger.warning(f"  Include path not found: {item}")
    return staged


def _fetch_each_to_named_dirs(
    fetch_cfg: list[dict[str, Any]],
    staging_root: Path,
    root: Path,
    verbose: bool,
    name_filter: str | None,
    dry_run: bool = False,
) -> list[Path]:
    staged: list[Path] = []
    if not fetch_cfg:
        return staged
    logger.info(f"[Remote] Fetching {len(fetch_cfg)} source(s) ...")
    for idx, src in enumerate(fetch_cfg, start=1):
        name = src.get("name") or f"fetched-{idx}"
        if name_filter and name != name_filter:
            continue

        if dry_run:
            ftype = (src.get("type") or "url").lower()
            logger.info(f"[dry-run] Would fetch: {name} (type: {ftype})")
            if ftype == "url":
                url = src.get("url")
                logger.info(f"[dry-run]   from URL: {url}")
            elif ftype == "mozilla":
                logger.info("[dry-run]   from Mozilla CA Bundle: https://curl.se/ca/cacert.pem")
            elif ftype == "api":
                endpoint = src.get("endpoint") or src.get("url")
                provider = src.get("provider") or "generic"
                logger.info(f"[dry-run]   from API: {endpoint} (provider: {provider})")
            elif ftype == "vault":
                mount_point = (
                    src.get("mount_point") or src.get("mount") or src.get("engine") or "secret"
                )
                path = src.get("path")
                logger.info(f"[dry-run]   from Vault: {mount_point}/{path}")
            elif ftype == "gcs":
                bucket = src.get("bucket")
                object_path = src.get("object_path") or src.get("object") or src.get("path")
                logger.info(f"[dry-run]   from GCS: gs://{bucket}/{object_path}")
            elif ftype == "azure_blob":
                container = src.get("container")
                blob_name = src.get("blob_name")
                account_name = src.get("account_name") or "default"
                logger.info(f"[dry-run]   from Azure Blob: {account_name}/{container}/{blob_name}")
            elif ftype == "s3":
                url_param = src.get("url")
                bucket = src.get("bucket")
                key_param = src.get("key")
                if url_param:
                    logger.info(f"[dry-run]   from S3: {url_param}")
                elif bucket and key_param:
                    logger.info(f"[dry-run]   from S3: s3://{bucket}/{key_param}")
            logger.info(f"[dry-run]   to directory: {staging_root / 'fetch' / name}")
            continue

        # New structure: stage remote fetches under a dedicated 'fetch/<name>' subdirectory
        subdir = staging_root / "fetch" / name
        ensure_dir(subdir)
        try:
            out_paths = _fetch_from_config([src], subdir, root, verbose=verbose)
            staged.extend(out_paths)
        except click.ClickException:
            raise
    return staged


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--source-config-file",
    "source_config_file",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, path_type=Path),
    required=True,
    help="Path to a bundle config YAML to fetch from directly (reads include/exclude/fetch only)",
)
@click.option(
    "--fetch-name",
    "fetch_name",
    required=False,
    help="If provided, only run the fetch entry with this name; otherwise run all fetch entries",
)
@click.option(
    "--workspace-root",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".").resolve(),
    help="Workspace root directory used to resolve relative include/exclude paths (default: current dir)",
)
@click.option("--no-clean", is_flag=True, help="Do not clean staging directory before fetching")
@click.option(
    "--fetch-only",
    is_flag=True,
    help="Only perform remote fetches; skip copying local certificates from 'include'",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path("cert_sources") / "staged",
    help="Output directory for staged certificates (default: ./cert_sources/staged)",
)
@click.option("--verbose", is_flag=True, help="Show extra debug output for fetch operations")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without actually fetching or copying any files",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Emit machine-readable JSON output (suppresses human-readable output)",
)
def main(
    source_config_file: Path,
    fetch_name: str | None,
    workspace_root: Path,
    no_clean: bool,
    fetch_only: bool,
    output_dir: Path,
    verbose: bool,
    dry_run: bool,
    json_output: bool,
):
    """Fetch and stage certificate inputs declared in a bundle config.

    This command operates entirely on a single bundle config file and does not consult env/env configs.

        Steps:
      1) Create the staging directory (--output-dir)
            2) Create per-source subdirectories: 'include/' or named repo dirs for local paths, and 'fetch/<name>/' for each remote fetch entry
      3) Copy local includes (unless --fetch-only) and perform remote fetches into their respective subdirectories
      4) Summarize the resulting directory structure and file counts

    Use --dry-run to preview what would be fetched without making any changes.
    """
    json_errors = []
    local_count = 0

    if not json_output:
        # Unified banner
        print_banner("Fetcher")

        if dry_run:
            click.secho(
                "[DRY RUN MODE] No files will be fetched or copied\n", fg="yellow", bold=True
            )

    # Set logging level based on verbose flag
    if not json_output:
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        if verbose:
            logger.debug("Verbose mode enabled")
    else:
        # Suppress logging in JSON mode
        logger.setLevel(logging.CRITICAL)

    try:
        root = workspace_root.resolve()
        cfg = load_yaml(source_config_file, required=True, validate=validate_source_config)
        _validate_source_and_fetch_names(cfg)
        fetch_cfg = cfg.get("fetch") or []
        if not isinstance(fetch_cfg, list):
            raise click.ClickException("Config key 'fetch' must be a list of sources")

        # Determine source identifier for staging root
        source_name = cfg.get("source_name") or source_config_file.stem

        # Human-readable parity with builder: announce which source is being staged
        if not json_output:
            click.secho(f"Staging certificate source: {source_name}", fg="blue")

        # Prepare staging dir: <output_dir>/<source_name>
        # If output_dir is relative, resolve it against workspace_root
        if not output_dir.is_absolute():
            staging_root = (root / output_dir / source_name).resolve()
        else:
            staging_root = (output_dir / source_name).resolve()
        if not dry_run:
            ensure_dir(staging_root)
        if not no_clean and not dry_run:
            if not json_output:
                logger.info(f"Cleaning staging directory: {staging_root}")
            _clean_dir(staging_root)
            ensure_dir(staging_root)
        elif dry_run and not json_output:
            logger.info(f"[dry-run] Would use staging directory: {staging_root}")

        staged_paths: list[Path] = []
        if not fetch_only:
            local_paths = _stage_local_includes(cfg, staging_root, root, verbose, dry_run)
            staged_paths += local_paths
            local_count = len(local_paths)

        # Fetch remote sources
        staged_paths += _fetch_each_to_named_dirs(
            fetch_cfg, staging_root, root, verbose, fetch_name, dry_run
        )

        # Summarize directory structure and counts
        if not dry_run and staging_root.exists():
            if not json_output:
                click.secho("\n[SUMMARY] Staged artifacts:", fg="blue")
            total = 0
            for sub in sorted(staging_root.iterdir()):
                if not sub.is_dir():
                    continue
                files = [p for p in sorted(sub.rglob("*")) if p.is_file()]
                count = len(files)
                total += count
                if not json_output:
                    click.secho(f"  - {sub.name}/ : {count} file(s)", fg="blue")
            if not json_output:
                click.secho(f"  Total: {total} file(s)\n", fg="blue")
        elif dry_run and not json_output:
            click.secho("\n[SUMMARY] [dry-run] Would stage artifacts to:", fg="yellow")
            click.secho(f"  {staging_root}", fg="yellow")
            if not no_clean:
                click.secho(
                    "  [dry-run] Would clean staging directory before fetching", fg="yellow"
                )
            click.secho("", fg="yellow")  # Empty line for formatting

        if json_output:
            from bundlecraft.helpers.json_output import create_fetch_response, emit_json

            emit_json(
                create_fetch_response(
                    success=True,
                    source_name=source_name,
                    staging_path=str(staging_root),
                    fetched_sources=len(fetch_cfg),
                    local_sources=local_count if not fetch_only else 0,
                    total_files=len(staged_paths),
                    dry_run=dry_run,
                )
            )
        else:
            if dry_run:
                # Uniform success icon and color for dry-run completion
                click.secho("✅ [dry-run] Fetch simulation completed.", fg="yellow")
            else:
                # Uniform success icon and color
                click.secho("✅ Fetch completed.", fg="green")

    except click.ClickException as e:
        error_msg = str(e)
        if json_output:
            json_errors.append(error_msg)
            from bundlecraft.helpers.json_output import create_fetch_response, emit_json

            emit_json(
                create_fetch_response(
                    success=False, source_name="", staging_path="", errors=json_errors
                )
            )
        else:
            click.secho(f"[ERROR] {error_msg}", fg="red", err=True)
        sys.exit(ExitCode.CONFIG_ERROR)
    except Exception as e:
        error_msg = f"Fetch failed: {e}"
        if json_output:
            json_errors.append(error_msg)
            from bundlecraft.helpers.json_output import create_fetch_response, emit_json

            emit_json(
                create_fetch_response(
                    success=False, source_name="", staging_path="", errors=json_errors
                )
            )
        else:
            click.secho(f"[ERROR] {error_msg}", fg="red", err=True)
        sys.exit(ExitCode.FETCH_ERROR)


if __name__ == "__main__":
    main()
