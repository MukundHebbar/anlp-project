"""Central project paths used by generation and evaluation commands."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(
    os.environ.get("ANLP_PROJECT_ROOT", Path(__file__).resolve().parents[2])
).resolve()
DATA_DIR = PROJECT_ROOT / "data"
PROMPTS_DIR = DATA_DIR / "prompts"
MANIFESTS_DIR = DATA_DIR / "manifests"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
LEGACY_ARCHIVE_DIR = PROJECT_ROOT / "local" / "archive" / "legacy"
ENV_FILE = PROJECT_ROOT / ".env"


def project_path(*parts: str) -> Path:
    """Return a path rooted in this project."""

    return PROJECT_ROOT.joinpath(*parts)
