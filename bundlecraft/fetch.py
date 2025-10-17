#!/usr/bin/env python3
"""
fetch.py
First stage of the BundleCraft pipeline: securely fetch and stage certificate sources.

Design choices per ADR-0002 and user guidance:
 - No persistent caching; fetched artifacts are staged under sources/fetched/<env>/<bundle>/
 - Staging directory is cleaned at the start of each fetch run
 - Only trusted origins: HTTPS/file URLs supported; optional content SHA256 pinning
 - Staged files are treated the same as local sources by the build stage
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from bundlecraft.fetchers.api import fetch_api
from bundlecraft.fetchers.http import fetch_url
from bundlecraft.fetchers.vault import fetch_vault
from bundlecraft.helpers.utils import ensure_dir, load_yaml, sha256_file

CURRENT_DIR = Path(__file__).resolve().parent


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


def _fetch_from_config(fetch_cfg: list[dict[str, Any]], dest_dir: Path, root: Path) -> list[Path]:
    outputs: list[Path] = []
    provenance: list[dict[str, Any]] = []

    for idx, src in enumerate(fetch_cfg, start=1):
        ftype = (src.get("type") or "url").lower()
        name = src.get("name") or f"fetched-{idx}"
        verify = src.get("verify") or {}

        if ftype == "url":
            url = src.get("url")
            if not url:
                raise click.ClickException("Fetch source missing 'url'")
            out_path = fetch_url(url, dest_dir, name=name, verify=verify, root=root)
        elif ftype == "api":
            endpoint = src.get("endpoint") or src.get("url")
            if not endpoint:
                raise click.ClickException("API fetch source requires 'endpoint' (or 'url')")
            provider = src.get("provider")
            token_ref = src.get("token_ref")
            headers = (verify or {}).get("headers") if isinstance(verify, dict) else None
            out_path = fetch_api(
                endpoint,
                dest_dir,
                name=name,
                provider=provider,
                token_ref=token_ref,
                headers=headers,
                verify=verify if isinstance(verify, dict) else None,
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
        else:
            raise click.ClickException(f"Unsupported fetch type: {ftype}")

        actual_sha = sha256_file(out_path)
        if "sha256" in verify:
            expected_sha256 = str(verify.get("sha256"))
            if actual_sha.lower() != expected_sha256.lower():
                # Remove the file immediately to avoid accidental use
                out_path.unlink(missing_ok=True)
                raise click.ClickException(
                    f"SHA256 mismatch for {name}: expected {expected_sha256}, got {actual_sha}"
                )

        outputs.append(out_path)
        provenance.append(
            {
                "name": name,
                "origin": src,
                "staged_path": str(out_path.relative_to(root)),
                "sha256": actual_sha,
            }
        )

    _write_provenance(dest_dir, provenance)
    return outputs


def run_fetch(
    env: str, bundle: str, workspace_root: Path, no_clean: bool = False, offline: bool = False
) -> list[Path]:
    """Programmatic entrypoint to fetch-and-stage.

    Returns list of staged file paths. No-op (empty list) if no fetch section.
    Raises ClickException on validation errors.
    """
    root = workspace_root.resolve()
    config_dir = root / "config"
    sources_dir = root / "sources"

    # Ensure basic structure exists
    ensure_dir(sources_dir)

    # Load config
    _ = load_yaml(config_dir / "envs" / f"{env}.yaml", required=True)
    bundle_cfg = load_yaml(config_dir / "bundles" / f"{bundle}.yaml", required=True)
    fetch_cfg = bundle_cfg.get("fetch") or []
    if not isinstance(fetch_cfg, list):
        raise click.ClickException("Config key 'fetch' must be a list of sources")
    if not fetch_cfg:
        return []

    dest_dir = sources_dir / "fetched" / env / bundle
    ensure_dir(dest_dir)
    if not no_clean:
        _clean_dir(dest_dir)
        ensure_dir(dest_dir)

    if offline:
        # In offline mode, do not perform network calls. If any fetch entries exist, fail.
        raise click.ClickException("Offline mode is enabled but fetch entries are present.")
    outputs = _fetch_from_config(fetch_cfg, dest_dir, root)
    return outputs


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--env", required=True, help="Environment name (e.g., dev, prod, dmz)")
@click.option("--bundle", required=True, help="Bundle name (e.g., internal, external)")
@click.option(
    "--workspace-root",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".").resolve(),
    help="Workspace root directory containing config/ and sources/ (defaults to current repo)",
)
@click.option(
    "--no-clean",
    is_flag=True,
    help="Do not clean staging directory before fetching (default is to clean)",
)
@click.option("--offline", is_flag=True, help="Fail if 'fetch' is required; do not contact network")
def main(env: str, bundle: str, workspace_root: Path, no_clean: bool, offline: bool):
    """Fetch and stage certificate inputs declared in bundle config (CLI)."""
    click.secho("\n🔐 BundleCraft Fetcher\n----------------------", fg="cyan")
    try:
        outputs = run_fetch(env, bundle, workspace_root, no_clean=no_clean, offline=offline)
    except click.ClickException as e:
        click.secho(f"[ERROR] {e}", fg="red", err=True)
        sys.exit(2)
    except Exception as e:
        click.secho(f"[ERROR] Fetch failed: {e}", fg="red", err=True)
        sys.exit(2)

    if not outputs:
        click.secho("[INFO] No 'fetch' entries found in bundle config. Nothing to do.", fg="yellow")
        sys.exit(0)

    for p in outputs:
        click.secho(f"[OK] Staged: {p}", fg="green")

    click.secho("[SUCCESS] Fetch completed. You can now run 'bundlecraft build'", fg="green")


if __name__ == "__main__":
    main()
