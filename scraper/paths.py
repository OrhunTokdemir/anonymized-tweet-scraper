"""Project-relative paths (no third-party imports, so tests run without deps)."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_path(value: str) -> Path:
    """Relative paths are relative to the project folder, not the current directory."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path
