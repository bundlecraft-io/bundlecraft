#!/usr/bin/env python3
"""
Detect environment bundles from config/envs/*.yaml and emit JSON for CI matrix.

Output format: a JSON array of objects with keys { env, bundle, output_root }.
"""
from __future__ import annotations

import glob
import json
import os
import sys

try:
    import yaml  # type: ignore
except Exception as e:  # pragma: no cover - CI-friendly message
    raise SystemExit(f"PyYAML is required to detect env bundles: {e}") from e


def parse_envs(arg: str | None) -> set[str]:
    if not arg:
        return set()
    return {s.strip() for s in str(arg).split(",") if s and s.strip()}


def main() -> None:
    # Optional flags:
    #   --envs "dev,qa,prod" to select a subset
    #   --github-release-only to include only envs with github-release enabled
    sel_envs: set[str] = set()
    github_release_only = False
    args = sys.argv[1:]
    # Parse --envs
    if "--envs" in args:
        try:
            idx = args.index("--envs")
            sel_envs = parse_envs(args[idx + 1])
        except Exception:
            print("::warning::--envs requires a comma-separated value (e.g., dev,qa)")
    # Parse --github-release-only
    if "--github-release-only" in args:
        github_release_only = True
    env_bundles: list[dict[str, str]] = []
    # Scan env configs
    paths = sorted(glob.glob("config/envs/*.yaml"))
    for path in paths:
        base = os.path.basename(path)
        if base.startswith("example"):
            continue
        file_stem_env = os.path.splitext(base)[0]
        try:
            with open(path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"::warning::Failed to parse {path}: {e}")
            cfg = {}

        # Use the filename stem (without .yaml) as the environment identifier for CLI
        # This is what the CLI expects in --env parameter to locate config/envs/<env>.yaml
        env = file_stem_env

        # If a subset of environments was specified, filter here using the resolved name
        if sel_envs and env not in sel_envs:
            continue

        if github_release_only:
            dist = cfg.get("distribution_metadata") or cfg.get("distribution") or {}
            release_entries = []
            if isinstance(dist, dict):
                # Support both new and old keys if present
                release_entries = dist.get("bundles") or dist.get("targets") or []
            enabled = any(
                isinstance(t, dict)
                and t.get("type") == "github-release"
                and (t.get("enabled") is True)
                for t in release_entries
            )
            if not enabled:
                continue
        bundles = cfg.get("bundles") or {}
        # Resolve output_root with same logic as builder:
        # build_path is always rooted under dist/, and normalized
        build_path_cfg = cfg.get("build_path")
        if build_path_cfg:
            # Strip leading slashes, ../, and dist/ prefix if present
            build_path_clean = str(build_path_cfg).strip("/").replace("..", "")
            if build_path_clean.startswith("dist/"):
                build_path_clean = build_path_clean[5:]
            # Root under dist/
            output_root = f"dist/{build_path_clean}".rstrip("/")
        else:
            # Default: dist (builder will append env/bundle)
            output_root = "dist"

        if isinstance(bundles, dict):
            for b in sorted(bundles.keys()):
                env_bundles.append({"env": env, "bundle": str(b), "output_root": output_root})
        elif isinstance(bundles, list):
            for b in sorted(bundles):
                env_bundles.append({"env": env, "bundle": str(b), "output_root": output_root})

    print(json.dumps(env_bundles))


if __name__ == "__main__":
    main()
