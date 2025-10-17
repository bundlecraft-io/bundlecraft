#!/usr/bin/env python3
"""
trust_matrix.py

Generate a trust matrix showing which environments (rows) trust which bundles (columns),
based on environment composition defined in config/envs/*.yaml.

Trust = union of all bundles referenced by any target in an environment's `targets.<name>.includes`.

Outputs:
  - table (unicode box table for terminals)
  - markdown (GitHub-friendly table)
  - csv
  - json (structured data)

Usage:
  python scripts/trust_matrix.py --config-dir config --format table
  python scripts/trust_matrix.py --format markdown --output TRUST_MATRIX.md
  python scripts/trust_matrix.py --format json --output trust-matrix.json

Notes:
  - Back-compat: if an env file defines `bundle_targets` as a list, those will be treated as trusted bundles.
  - Requires PyYAML.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    print("[ERROR] PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    raise


def load_yaml(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def collect_env_trust(
    config_dir: Path,
) -> tuple[list[str], list[str], dict[str, set[str]], dict[str, dict[str, list[str]]]]:
    envs_dir = config_dir / "envs"
    if not envs_dir.exists():
        raise FileNotFoundError(f"Missing envs directory: {envs_dir}")

    env_to_bundles: dict[str, set[str]] = {}
    env_to_targets: dict[str, dict[str, list[str]]] = {}

    for env_path in sorted(envs_dir.glob("*.yaml")):
        env_name = env_path.stem
        data = load_yaml(env_path)
        bundles_for_env: set[str] = set()
        targets_map: dict[str, list[str]] = {}

        # Composition-aware schema
        targets = data.get("targets") or {}
        if isinstance(targets, dict):
            for tgt_name, tgt_cfg in targets.items():
                includes = tgt_cfg.get("includes") if isinstance(tgt_cfg, dict) else None
                if isinstance(includes, list):
                    targets_map[tgt_name] = [str(x) for x in includes]
                    bundles_for_env.update(str(x) for x in includes)
                elif isinstance(includes, str):
                    targets_map[tgt_name] = [includes]
                    bundles_for_env.add(includes)

        # Back-compat: flat list of bundle targets
        legacy = data.get("bundle_targets")
        if isinstance(legacy, list):
            for b in legacy:
                bundles_for_env.add(str(b))

        if bundles_for_env:
            env_to_bundles[env_name] = bundles_for_env
            env_to_targets[env_name] = targets_map

    # All unique bundles as columns
    all_bundles: list[str] = sorted({b for s in env_to_bundles.values() for b in s})
    all_envs: list[str] = sorted(env_to_bundles.keys())
    return all_envs, all_bundles, env_to_bundles, env_to_targets


def render_table(envs: list[str], bundles: list[str], env_to_bundles: dict[str, set[str]]) -> str:
    if not envs or not bundles:
        return "(no data)"

    # Build rows
    header = ["environment \\ bundle"] + bundles
    rows: list[list[str]] = [header]
    for env in envs:
        row = [env]
        trusted = env_to_bundles.get(env, set())
        for b in bundles:
            row.append("✔" if b in trusted else "")
        rows.append(row)

    # Compute column widths
    widths = [max(len(r[c]) for r in rows) for c in range(len(rows[0]))]

    def hr(char_left: str, char_mid: str, char_right: str) -> str:
        pieces = []
        for w in widths:
            pieces.append("─" * (w + 2))
        return char_left + char_mid.join(pieces) + char_right

    top = hr("┌", "┬", "┐")
    mid = hr("├", "┼", "┤")
    bot = hr("└", "┴", "┘")

    def fmt_row(cols: list[str]) -> str:
        padded = [f" {col}{' ' * (w - len(col))} " for col, w in zip(cols, widths, strict=False)]
        return "│" + "│".join(padded) + "│"

    lines = [top, fmt_row(rows[0]), mid]
    for r in rows[1:]:
        lines.append(fmt_row(r))
    lines.append(bot)
    return "\n".join(lines)


def render_markdown(
    envs: list[str], bundles: list[str], env_to_bundles: dict[str, set[str]]
) -> str:
    if not envs or not bundles:
        return "(no data)"
    header = ["environment \\ bundle"] + bundles
    sep = ["---"] * len(header)
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    for env in envs:
        row = [env] + ["✔" if b in env_to_bundles.get(env, set()) else "" for b in bundles]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_csv(envs: list[str], bundles: list[str], env_to_bundles: dict[str, set[str]]) -> str:
    from io import StringIO

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["environment \\ bundle", *bundles])
    for env in envs:
        row = [env] + [("1" if b in env_to_bundles.get(env, set()) else "0") for b in bundles]
        writer.writerow(row)
    return buf.getvalue()


def render_json(
    envs: list[str],
    bundles: list[str],
    env_to_bundles: dict[str, set[str]],
    env_to_targets: dict[str, dict[str, list[str]]],
) -> str:
    payload = {
        "bundles": bundles,
        "environments": {
            env: {
                "trusts": sorted(list(env_to_bundles.get(env, set()))),
                "targets": env_to_targets.get(env, {}),
            }
            for env in envs
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate environment/bundle trust matrix from config"
    )
    parser.add_argument(
        "--config-dir", default="config", help="Path to config directory (default: config)"
    )
    parser.add_argument(
        "--format",
        choices=["table", "markdown", "csv", "json"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument("--output", "-o", help="Write output to file instead of stdout")
    args = parser.parse_args(argv)

    config_dir = Path(args.config_dir)
    try:
        envs, bundles, env_to_bundles, env_to_targets = collect_env_trust(config_dir)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2

    if args.format == "table":
        out = render_table(envs, bundles, env_to_bundles)
    elif args.format == "markdown":
        out = render_markdown(envs, bundles, env_to_bundles)
    elif args.format == "csv":
        out = render_csv(envs, bundles, env_to_bundles)
    else:
        out = render_json(envs, bundles, env_to_bundles, env_to_targets)

    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
