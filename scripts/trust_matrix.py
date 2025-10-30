#!/usr/bin/env python3
"""
trust_matrix.py

Generate a trust matrix showing which environments (rows, using config 'name') build which bundles (columns),
and which sources are trusted in each bundle, based on config/envs/*.yaml and config/cert_sources/*.yaml.

Outputs:
    - table (unicode box table for terminals): environments × bundles
    - markdown (GitHub-friendly table): environments × bundles
    - csv: environments × bundles
    - json: structured mapping of environments → bundles → sources

Usage:
    python scripts/trust_matrix.py --config-dir config --format table
    python scripts/trust_matrix.py --format markdown --output TRUST_MATRIX.md
    python scripts/trust_matrix.py --format json --output trust-matrix.json

Notes:
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


def collect_env_trust(config_dir: Path):
    envs_dir = config_dir / "envs"
    sources_dir = config_dir / "sources"
    if not envs_dir.exists():
        raise FileNotFoundError(f"Missing envs directory: {envs_dir}")
    if not sources_dir.exists():
        raise FileNotFoundError(f"Missing sources directory: {sources_dir}")

    envs = []
    env_to_bundles = {}
    env_to_bundle_sources = {}
    all_sources_set = set()

    for env_path in sorted(envs_dir.glob("*.yaml")):
        data = load_yaml(env_path)
        env_name = data.get("name") or env_path.stem
        envs.append(env_name)
        bundles = data.get("bundles") or {}
        bundle_names = list(bundles.keys())
        env_to_bundles[env_name] = set(bundle_names)
        env_to_bundle_sources[env_name] = {}
        for b_name, b_cfg in bundles.items():
            include_sources = b_cfg.get("include_sources") if isinstance(b_cfg, dict) else None
            if isinstance(include_sources, list):
                env_to_bundle_sources[env_name][b_name] = [str(x) for x in include_sources]
                all_sources_set.update(str(x) for x in include_sources)
            elif isinstance(include_sources, str):
                env_to_bundle_sources[env_name][b_name] = [include_sources]
                all_sources_set.add(include_sources)

    # All unique bundle names as columns
    all_bundles = sorted({b for s in env_to_bundles.values() for b in s})
    # All unique sources as columns
    all_sources = sorted(all_sources_set)

    # Bundle to sources mapping (across all envs)
    bundle_to_sources = {}
    for env in envs:
        for b in env_to_bundle_sources[env]:
            bundle_to_sources.setdefault(b, set()).update(env_to_bundle_sources[env][b])

    # Env to sources mapping (union of all sources in all bundles)
    env_to_sources = {}
    for env in envs:
        sources = set()
        for b in env_to_bundle_sources[env].values():
            sources.update(b)
        env_to_sources[env] = sources

    return (
        envs,
        all_bundles,
        all_sources,
        env_to_bundles,
        env_to_bundle_sources,
        bundle_to_sources,
        env_to_sources,
    )


def render_table(envs, bundles, env_to_bundles):
    if not envs or not bundles:
        return "(no data)"
    header = ["environment \\ bundle"] + bundles
    rows = [header]
    for env in envs:
        row = [env]
        present = env_to_bundles.get(env, set())
        for b in bundles:
            row.append("✔" if b in present else "")
        rows.append(row)
    widths = [max(len(r[c]) for r in rows) for c in range(len(rows[0]))]

    def hr(char_left, char_mid, char_right):
        pieces = ["─" * (w + 2) for w in widths]
        return char_left + char_mid.join(pieces) + char_right

    top = hr("┌", "┬", "┐")
    mid = hr("├", "┼", "┤")
    bot = hr("└", "┴", "┘")

    def fmt_row(cols):
        padded = [f" {col}{' ' * (w - len(col))} " for col, w in zip(cols, widths, strict=True)]
        return "│" + "│".join(padded) + "│"

    lines = [top, fmt_row(rows[0]), mid]
    for r in rows[1:]:
        lines.append(fmt_row(r))
    lines.append(bot)
    return "\n".join(lines)


def render_bundle_source_table(bundles, sources, bundle_to_sources):
    if not bundles or not sources:
        return "(no data)"
    header = ["bundle \\ source"] + sources
    rows = [header]
    for b in bundles:
        row = [b]
        present = bundle_to_sources.get(b, set())
        for s in sources:
            row.append("✔" if s in present else "")
        rows.append(row)
    widths = [max(len(r[c]) for r in rows) for c in range(len(rows[0]))]

    def hr(char_left, char_mid, char_right):
        pieces = ["─" * (w + 2) for w in widths]
        return char_left + char_mid.join(pieces) + char_right

    top = hr("┌", "┬", "┐")
    mid = hr("├", "┼", "┤")
    bot = hr("└", "┴", "┘")

    def fmt_row(cols):
        padded = [f" {col}{' ' * (w - len(col))} " for col, w in zip(cols, widths, strict=True)]
        return "│" + "│".join(padded) + "│"

    lines = [top, fmt_row(rows[0]), mid]
    for r in rows[1:]:
        lines.append(fmt_row(r))
    lines.append(bot)
    return "\n".join(lines)


def render_env_source_table(envs, sources, env_to_sources):
    if not envs or not sources:
        return "(no data)"
    header = ["environment \\ source"] + sources
    rows = [header]
    for env in envs:
        row = [env]
        present = env_to_sources.get(env, set())
        for s in sources:
            row.append("✔" if s in present else "")
        rows.append(row)
    widths = [max(len(r[c]) for r in rows) for c in range(len(rows[0]))]

    def hr(char_left, char_mid, char_right):
        pieces = ["─" * (w + 2) for w in widths]
        return char_left + char_mid.join(pieces) + char_right

    top = hr("┌", "┬", "┐")
    mid = hr("├", "┼", "┤")
    bot = hr("└", "┴", "┘")

    def fmt_row(cols):
        padded = [f" {col}{' ' * (w - len(col))} " for col, w in zip(cols, widths, strict=True)]
        return "│" + "│".join(padded) + "│"

    lines = [top, fmt_row(rows[0]), mid]
    for r in rows[1:]:
        lines.append(fmt_row(r))
    lines.append(bot)
    return "\n".join(lines)


def render_markdown(envs, bundles, env_to_bundles):
    if not envs or not bundles:
        return "(no data)"
    header = ["environment \\ bundle"] + bundles
    sep = ["---"] * len(header)
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    for env in envs:
        row = [env] + ["✔" if b in env_to_bundles.get(env, set()) else "" for b in bundles]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_bundle_source_markdown(bundles, sources, bundle_to_sources):
    if not bundles or not sources:
        return "(no data)"
    header = ["bundle \\ source"] + sources
    sep = ["---"] * len(header)
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    for b in bundles:
        row = [b] + ["✔" if s in bundle_to_sources.get(b, set()) else "" for s in sources]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_env_source_markdown(envs, sources, env_to_sources):
    if not envs or not sources:
        return "(no data)"
    header = ["environment \\ source"] + sources
    sep = ["---"] * len(header)
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    for env in envs:
        row = [env] + ["✔" if s in env_to_sources.get(env, set()) else "" for s in sources]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_csv(envs, bundles, env_to_bundles):
    from io import StringIO

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["environment \\ bundle", *bundles])
    for env in envs:
        row = [env] + [("1" if b in env_to_bundles.get(env, set()) else "0") for b in bundles]
        writer.writerow(row)
    return buf.getvalue()


def render_bundle_source_csv(bundles, sources, bundle_to_sources):
    from io import StringIO

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["bundle \\ source", *sources])
    for b in bundles:
        row = [b] + [("1" if s in bundle_to_sources.get(b, set()) else "0") for s in sources]
        writer.writerow(row)
    return buf.getvalue()


def render_env_source_csv(envs, sources, env_to_sources):
    from io import StringIO

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["environment \\ source", *sources])
    for env in envs:
        row = [env] + [("1" if s in env_to_sources.get(env, set()) else "0") for s in sources]
        writer.writerow(row)
    return buf.getvalue()


def render_json(
    envs, bundles, sources, env_to_bundles, env_to_bundle_sources, bundle_to_sources, env_to_sources
):
    payload = {
        "environments": {
            env: {
                "bundles": sorted(list(env_to_bundles.get(env, set()))),
                "sources": sorted(list(env_to_sources.get(env, set()))),
                "bundle_sources": {
                    b: env_to_bundle_sources[env].get(b, []) for b in env_to_bundle_sources[env]
                },
            }
            for env in envs
        },
        "bundles": {b: sorted(list(bundle_to_sources.get(b, set()))) for b in bundles},
        "sources": sources,
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
        (
            envs,
            bundles,
            sources,
            env_to_bundles,
            env_to_bundle_sources,
            bundle_to_sources,
            env_to_sources,
        ) = collect_env_trust(config_dir)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2

    if args.format == "table":
        print("\n[Environments × Bundles]")
        print(render_table(envs, bundles, env_to_bundles))
        print("\n[Bundles × Sources]")
        print(render_bundle_source_table(bundles, sources, bundle_to_sources))
        print("\n[Environments × Sources]")
        print(render_env_source_table(envs, sources, env_to_sources))
        out = ""
    elif args.format == "markdown":
        out = "\n[Environments × Bundles]\n" + render_markdown(envs, bundles, env_to_bundles)
        out += "\n\n[Bundles × Sources]\n" + render_bundle_source_markdown(
            bundles, sources, bundle_to_sources
        )
        out += "\n\n[Environments × Sources]\n" + render_env_source_markdown(
            envs, sources, env_to_sources
        )
    elif args.format == "csv":
        out = "[Environments × Bundles]\n" + render_csv(envs, bundles, env_to_bundles)
        out += "\n[Bundles × Sources]\n" + render_bundle_source_csv(
            bundles, sources, bundle_to_sources
        )
        out += "\n[Environments × Sources]\n" + render_env_source_csv(envs, sources, env_to_sources)
    else:
        out = render_json(
            envs,
            bundles,
            sources,
            env_to_bundles,
            env_to_bundle_sources,
            bundle_to_sources,
            env_to_sources,
        )

    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
