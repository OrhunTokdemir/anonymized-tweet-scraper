"""Responsible-use notice shown on first start (standard library only, so tests run without deps).

The text lives in RESPONSIBLE_USE.md (bundled with builds). It is guidance only:
the MIT License alone governs use of the software. Its first line carries a
version number; when the user dismisses the notice, that version is stored
locally in APP_DIR/guidelines-read.txt, so the notice comes back only when the
text changes. Nothing is ever sent anywhere.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .paths import resource_path

GUIDELINES_FILE = "RESPONSIBLE_USE.md"
READ_FILE = "guidelines-read.txt"
_VERSION_RE = re.compile(r"<!--\s*guidelines-version:\s*(\d+)\s*-->")


def load_guidelines(path: Path | None = None) -> tuple[int, str]:
    """-> (version, markdown text without the version comment)."""
    text = (path or resource_path(GUIDELINES_FILE)).read_text(encoding="utf-8")
    m = _VERSION_RE.search(text)
    if not m:
        raise ValueError(f"{GUIDELINES_FILE} has no '<!-- guidelines-version: N -->' line")
    return int(m.group(1)), _VERSION_RE.sub("", text, count=1).lstrip()


def read_info(app_dir: Path) -> tuple[int, str] | None:
    """-> (version, date) of the last time the notice was dismissed, or None."""
    try:
        text = (app_dir / READ_FILE).read_text(encoding="utf-8")
    except OSError:
        return None
    fields = dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
    try:
        return int(fields.get("version", "")), fields.get("read", "")
    except ValueError:
        return None


def is_read(app_dir: Path, version: int) -> bool:
    info = read_info(app_dir)
    return info is not None and info[0] == version


def record_read(app_dir: Path, version: int) -> None:
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / READ_FILE).write_text(
        f"version={version}\nread={date.today().isoformat()}\n", encoding="utf-8")
