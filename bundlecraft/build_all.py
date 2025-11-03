#!/usr/bin/env python3
"""
Build-all command for BundleCraft.

Discovers and builds all environment configurations.
"""

import glob
import json
from pathlib import Path

import click
import yaml

import bundlecraft.builder as builder_mod
from bundlecraft.builder import main as build_main


@click.command(name="build-all", context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--envs-path",
    type=str,
    help=(
        "Path or glob to discover env yaml files. "
        "If a directory, scans for *.yaml inside. "
        "Relative paths are resolved under config/envs/. "
        "Examples: 'my_github_envs', 'my_github_envs/*.yaml', 'config/envs/custom/*.yaml'."
    ),
)
@click.option("--skip-fetch", is_flag=True, help="Skip fetch stage; use existing staged sources")
@click.option("--skip-verify", is_flag=True, help="Skip verification stage")
@click.option(
    "--output-root",
    type=str,
    default="dist",
    help="Root directory for build outputs (default: ./dist)",
)
@click.option("--verbose", is_flag=True, help="Enable verbose output")
@click.option("--force", is_flag=True, help="Overwrite existing output files")
@click.option("--dry-run", is_flag=True, help="Show actions without writing files")
@click.option("--sign", is_flag=True, help="Sign artifacts with GPG")
@click.option("--gpg-key-id", type=str, help="GPG key ID to use for signing")
@click.option("--no-sbom", is_flag=True, help="Skip SBOM generation")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON output")
@click.option("--keep-temp", is_flag=True, help="Preserve temp build dirs on failure")
@click.option(
    "--print-plan",
    is_flag=True,
    help="Show which environment configs would be built and exit without building",
)
@click.option(
    "--recursive",
    is_flag=True,
    help="Recursively discover env configs in subdirectories (e.g., **/*.yaml)",
)
def main(
    envs_path: str | None,
    skip_fetch: bool,
    skip_verify: bool,
    output_root: str,
    verbose: bool,
    force: bool,
    dry_run: bool,
    sign: bool,
    gpg_key_id: str | None,
    no_sbom: bool,
    json_output: bool,
    keep_temp: bool,
    print_plan: bool,
    recursive: bool,
):
    """Discover all environments under config/envs/ and build each one.

    This ingrains the logic from the detect script so Docker and Python package
    users can simply run a single command without pre-computing a matrix.
    """
    # Discover env config files
    default_base = Path(builder_mod.CONFIG_DIR) / "envs"
    pattern: str
    if envs_path:
        p = Path(envs_path).expanduser()
        # Interpret relative paths under default_base
        if not p.is_absolute():
            p = (default_base / p).resolve()
        # If a directory, scan for *.yaml (or **/*.yaml if recursive)
        if p.exists() and p.is_dir():
            pattern = str(p / ("**/*.yaml" if recursive else "*.yaml"))
        else:
            # Assume it's a file or glob pattern
            pattern = str(p)
    else:
        pattern = str(default_base / ("**/*.yaml" if recursive else "*.yaml"))

    env_files = sorted(glob.glob(pattern, recursive=recursive))
    chosen: list[tuple[str, dict]] = []  # (env_stem, cfg)

    for path in env_files:
        base = Path(path).name
        if base.startswith("example"):
            continue
        env_stem = Path(base).stem

        try:
            with open(path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except Exception as e:  # pragma: no cover - friendly message
            click.echo(f"::warning::Failed to parse {path}: {e}")
            cfg = {}

        chosen.append((env_stem, cfg))

    if not chosen:
        # Provide a helpful message that includes the resolved pattern
        raise click.ClickException(f"No environments found to build (pattern: {pattern}).")

    # If --print-plan is provided, display plan and exit without building
    if print_plan:
        if json_output:
            plan_envs = []
            for env_stem, cfg in chosen:
                # Compute build path for this env (new behavior: always under dist/<env>)
                env_name_for_path = (cfg or {}).get("name") or env_stem
                safe_env = str(env_name_for_path).replace("/", "-").replace(" ", "-")
                build_path_cfg = (cfg or {}).get("build_path")
                if build_path_cfg:
                    # build_path is now a subdirectory within dist/<env>/
                    build_path_clean = str(build_path_cfg).strip("/")
                    build_output_base = str(Path("dist") / safe_env / build_path_clean)
                else:
                    build_output_base = str(Path("dist") / safe_env)

                plan_envs.append(
                    {
                        "env": env_stem,
                        "name": str((cfg or {}).get("name") or env_stem),
                        "path": str(Path(builder_mod.CONFIG_DIR) / "envs" / f"{env_stem}.yaml"),
                        "build_path": build_output_base,
                    }
                )

            plan = {
                "pattern": pattern,
                "environments": plan_envs,
            }
            click.echo(json.dumps(plan))
        else:
            click.secho(
                f"Plan: {len(chosen)} environment(s) will be built (pattern: {pattern})",
                fg="cyan",
            )
            for env_stem, cfg in chosen:
                env_name = str((cfg or {}).get("name") or env_stem)
                path_hint = Path(builder_mod.CONFIG_DIR) / "envs" / f"{env_stem}.yaml"

                # Compute build path for this env (new behavior: always under dist/<env>)
                env_name_for_path = (cfg or {}).get("name") or env_stem
                safe_env = str(env_name_for_path).replace("/", "-").replace(" ", "-")
                build_path_cfg = (cfg or {}).get("build_path")
                if build_path_cfg:
                    # build_path is now a subdirectory within dist/<env>/
                    build_path_clean = str(build_path_cfg).strip("/")
                    build_output_base = str(Path("dist") / safe_env / build_path_clean)
                else:
                    build_output_base = str(Path("dist") / safe_env)

                click.echo(f" - {env_name} ({env_stem}) -> {path_hint}")
                click.echo(f"   Build path: {build_output_base}/<bundle>")
        return

    # Run builds sequentially; each environment builds all its bundles by default
    ctx = click.get_current_context()
    failures: list[str] = []

    for env_stem, cfg in chosen:
        env_name = str((cfg or {}).get("name") or env_stem)
        if not json_output:
            click.secho(
                f"\n=== Building environment: {env_name} ({env_stem}) ===", fg="blue", bold=True
            )
        try:
            # Invoke the existing build command; omit --bundle to build all bundles in env
            ctx.invoke(
                build_main,
                env=env_stem,
                bundle=None,
                verify_only=False,
                skip_fetch=skip_fetch,
                skip_verify=skip_verify,
                output_root=output_root,
                verbose=verbose,
                force=force,
                dry_run=dry_run,
                sign=sign,
                gpg_key_id=gpg_key_id,
                generate_sbom=not no_sbom,
                no_sbom=no_sbom,
                json_output=json_output,
                keep_temp=keep_temp,
            )
        except SystemExit as e:
            # Capture non-zero exits to report at the end, continue other envs
            if e.code not in (0, None):
                failures.append(f"{env_name} ({env_stem}) -> exit {e.code}")
        except Exception as e:
            failures.append(f"{env_name} ({env_stem}) -> {e}")

    if failures:
        raise click.ClickException(
            "One or more environment builds failed:\n - " + "\n - ".join(failures)
        )


if __name__ == "__main__":
    main()
