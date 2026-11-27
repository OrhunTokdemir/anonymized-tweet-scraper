"""Terms of use shown on first start (standard library only, so tests run without deps).

The text lives in TERMS_OF_USE.md (bundled with builds). Its first line carries
a version number; acceptance is stored locally per version in
APP_DIR/terms-accepted.txt, so users are asked again only when the terms change.
Nothing is ever sent anywhere.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .paths import resource_path

TERMS_FILE = "TERMS_OF_USE.md"
ACCEPT_FILE = "terms-accepted.txt"
_VERSION_RE = re.compile(r"<!--\s*terms-version:\s*(\d+)\s*-->")


def load_terms(path: Path | None = None) -> tuple[int, str]:
    """-> (version, markdown text without the version comment)."""
    text = (path or resource_path(TERMS_FILE)).read_text(encoding="utf-8")
    m = _VERSION_RE.search(text)
    if not m:
        raise ValueError(f"{TERMS_FILE} has no '<!-- terms-version: N -->' line")
    return int(m.group(1)), _VERSION_RE.sub("", text, count=1).lstrip()


def accepted_info(app_dir: Path) -> tuple[int, str] | None:
    """-> (version, date) of the last acceptance, or None."""
    try:
        text = (app_dir / ACCEPT_FILE).read_text(encoding="utf-8")
    except OSError:
        return None
    fields = dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
    try:
        return int(fields.get("version", "")), fields.get("accepted", "")
    except ValueError:
        return None


def is_accepted(app_dir: Path, version: int) -> bool:
    info = accepted_info(app_dir)
    return info is not None and info[0] == version


def record_acceptance(app_dir: Path, version: int) -> None:
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / ACCEPT_FILE).write_text(
        f"version={version}\naccepted={date.today().isoformat()}\n", encoding="utf-8")
