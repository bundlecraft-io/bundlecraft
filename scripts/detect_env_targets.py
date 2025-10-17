#!/usr/bin/env python3
"""
Detect environment targets from config/envs/*.yaml and emit JSON for CI matrix.

Output format: a JSON array of objects with keys { env, target, output_root }.
"""
from __future__ import annotations

import glob
import json
import os

try:
    import yaml  # type: ignore
except Exception as e:  # pragma: no cover - CI-friendly message
    raise SystemExit(f"PyYAML is required to detect env targets: {e}") from e


def main() -> None:
    env_targets: list[dict[str, str]] = []
    for path in sorted(glob.glob("config/envs/*.yaml")):
        base = os.path.basename(path)
        if base.startswith("example"):
            continue
        env = os.path.splitext(base)[0]
        try:
            with open(path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"::warning::Failed to parse {path}: {e}")
            cfg = {}

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
