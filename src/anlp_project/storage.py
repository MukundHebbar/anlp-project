"""Small, deterministic JSON and text persistence helpers."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Input file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _atomic_replace(path: Path, writer: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            writer(temporary_file)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path:
            temporary = Path(temporary_path)
            if temporary.exists():
                temporary.unlink()


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON beside the destination, then replace it atomically."""

    def write(file: Any) -> None:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")

    _atomic_replace(path, write)


def atomic_write_text(path: Path, content: str) -> None:
    """Write text beside the destination, then replace it atomically."""

    _atomic_replace(path, lambda file: file.write(content))
