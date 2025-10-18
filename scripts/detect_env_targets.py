#!/usr/bin/env python3
"""
Detect craft targets from config/crafts/*.yaml (preferred) or legacy config/envs/*.yaml and emit JSON for CI matrix.

Output format: a JSON array of objects with keys { env, target, output_root }.
"""
from __future__ import annotations

import glob
import json
import os
import sys

try:
    import yaml  # type: ignore
except Exception as e:  # pragma: no cover - CI-friendly message
    raise SystemExit(f"PyYAML is required to detect env targets: {e}") from e


def parse_envs(arg: str | None) -> set[str]:
    if not arg:
        return set()
    return {s.strip() for s in str(arg).split(",") if s and s.strip()}


def main() -> None:
    # Optional flags:
    #   --envs "dev,qa,prod" to select a subset
    #   --github-release-only to include only crafts with github-release enabled
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
    env_targets: list[dict[str, str]] = []
    # Prefer crafts; also include legacy envs for back-compat
    paths = sorted(glob.glob("config/crafts/*.yaml")) or sorted(glob.glob("config/envs/*.yaml"))
    for path in paths:
        base = os.path.basename(path)
        if base.startswith("example"):
            continue
        env = os.path.splitext(base)[0]
        if sel_envs and env not in sel_envs:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"::warning::Failed to parse {path}: {e}")
            cfg = {}

        if github_release_only:
            dist = cfg.get("distribution_metadata") or cfg.get("distribution") or {}
            targets = dist.get("targets", []) if isinstance(dist, dict) else []
            enabled = any(
                isinstance(t, dict)
                and t.get("type") == "github-release"
                and (t.get("enabled") is True)
                for t in targets
            )
            if not enabled:
                continue

        targets = cfg.get("targets") or {}
        output_root = cfg.get("build_path") or "dist"
        output_root = str(output_root).rstrip("/")

        if isinstance(targets, dict):
            for t in sorted(targets.keys()):
                env_targets.append({"env": env, "target": str(t), "output_root": output_root})
        elif isinstance(targets, list):
            for t in sorted(targets):
                env_targets.append({"env": env, "target": str(t), "output_root": output_root})

    print(json.dumps(env_targets))


if __name__ == "__main__":
    main()
