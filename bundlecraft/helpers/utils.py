from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def load_yaml(path: Path, required: bool = True) -> dict[str, Any] | None:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing YAML file: {path}")
        return None
    try:
        import yaml  # PyYAML
    except ImportError as e:
        raise RuntimeError("PyYAML is required. Install with: pip install pyyaml") from e
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def list_files(folder: Path, suffixes: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for s in suffixes:
        out.extend(folder.rglob(f"*{s}"))
    return out
