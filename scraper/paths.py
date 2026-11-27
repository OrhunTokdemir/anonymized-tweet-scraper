"""Where the app keeps its files (no third-party imports, so tests run without deps).

Two kinds of files:
- APP_DIR:      writable files (.env, accounts.db, and data/ in source/portable mode).
- RESOURCE_DIR: read-only files shipped with the app (.env.example, lexicons/).
                In a PyInstaller build this is the extraction folder (sys._MEIPASS).

Three modes decide APP_DIR and the default CSV folder:
- source:   `python -m scraper` from a checkout. Everything in the repo folder,
            CSVs in data/ (unchanged behavior).
- portable: a built program with a file named `portable` next to it. Everything
            stays in that folder, CSVs in data/.
- standard: a built program without that file. Settings and accounts go to the
            per-user data folder, CSVs to <Documents>/anonymized-posts.
OUTPUT_DIR in .env overrides the CSV folder in every mode.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

APP_NAME = "anonymized-tweet-scraper"
OUTPUT_FOLDER_NAME = "anonymized-posts"  # inside Documents (standard mode)
PORTABLE_MARKER = "portable"

FROZEN = bool(getattr(sys, "frozen", False))
_REPO_ROOT = Path(__file__).resolve().parents[1]


def detect_mode(frozen: bool, exe_dir: Path) -> str:
    if not frozen:
        return "source"
    return "portable" if (exe_dir / PORTABLE_MARKER).is_file() else "standard"


def user_data_dir(platform: str, env: dict[str, str], home: Path) -> Path:
    """Per-user folder for settings and accounts (standard mode)."""
    if platform == "win32":
        base = env.get("APPDATA")
        return Path(base) / APP_NAME if base else home / "AppData" / "Roaming" / APP_NAME
    if platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    base = env.get("XDG_DATA_HOME", "").strip()
    # XDG paths must be absolute (POSIX rule: they start with "/")
    return (Path(base) if base.startswith("/") else home / ".local" / "share") / APP_NAME


def xdg_documents_dir(user_dirs_text: str | None, home: Path) -> Path | None:
    """XDG_DOCUMENTS_DIR from ~/.config/user-dirs.dirs (e.g. ~/Belgeler on Turkish systems)."""
    if not user_dirs_text:
        return None
    for line in user_dirs_text.splitlines():
        m = re.match(r'\s*XDG_DOCUMENTS_DIR\s*=\s*"?([^"]*)"?\s*$', line)
        if m:
            h = home.as_posix()
            value = m.group(1).replace("${HOME}", h).replace("$HOME", h)
            # must be absolute; "$HOME/" alone means "not set" per the XDG spec
            if value.startswith("/") and value.rstrip("/") != h.rstrip("/"):
                return Path(value)
    return None


def _windows_documents_dir() -> Path | None:
    """The real Documents folder, including OneDrive redirection."""
    try:
        import ctypes
        from ctypes import wintypes
        from uuid import UUID

        class GUID(ctypes.Structure):
            _fields_ = [("data1", wintypes.DWORD), ("data2", wintypes.WORD),
                        ("data3", wintypes.WORD), ("data4", wintypes.BYTE * 8)]

        u = UUID("{FDD39AD0-238F-46AF-ADB4-6C85480369C7}")  # FOLDERID_Documents
        guid = GUID(u.time_low, u.time_mid, u.time_hi_version,
                    (wintypes.BYTE * 8).from_buffer_copy(u.bytes[8:]))
        out = ctypes.c_wchar_p()
        shell32 = ctypes.windll.shell32  # type: ignore[attr-defined]
        if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)) != 0:
            return None
        try:
            return Path(out.value) if out.value else None
        finally:
            ctypes.windll.ole32.CoTaskMemFree(out)  # type: ignore[attr-defined]
    except Exception:
        return None


def documents_dir(platform: str, env: dict[str, str], home: Path) -> Path:
    if platform == "win32":
        return _windows_documents_dir() or home / "Documents"
    if platform != "darwin":
        config = Path(env.get("XDG_CONFIG_HOME") or home / ".config")
        try:
            text = (config / "user-dirs.dirs").read_text(encoding="utf-8")
        except OSError:
            text = None
        if found := xdg_documents_dir(text, home):
            return found
    return home / "Documents"


def resolve(frozen: bool, exe_dir: Path, platform: str, env: dict[str, str], home: Path
            ) -> tuple[str, Path, Path]:
    """-> (mode, app_dir, default_output_dir)."""
    mode = detect_mode(frozen, exe_dir)
    if mode == "source":
        return mode, _REPO_ROOT, _REPO_ROOT / "data"
    if mode == "portable":
        return mode, exe_dir, exe_dir / "data"
    return mode, user_data_dir(platform, env, home), documents_dir(platform, env, home) / OUTPUT_FOLDER_NAME


MODE, APP_DIR, DEFAULT_OUTPUT_DIR = resolve(
    FROZEN, Path(sys.executable).resolve().parent, sys.platform, dict(os.environ), Path.home()
)
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", _REPO_ROOT))

PROJECT_ROOT = APP_DIR  # backwards-compatible name


def ensure_app_dir() -> None:
    """Create APP_DIR (private to the user on Linux/macOS) before anything is written."""
    if not APP_DIR.exists():
        APP_DIR.mkdir(parents=True, exist_ok=True)
        if MODE == "standard" and os.name == "posix":
            os.chmod(APP_DIR, 0o700)


def project_path(value: str) -> Path:
    """Writable location: relative paths are relative to APP_DIR, not the current directory."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else APP_DIR / path


def output_dir(setting: str) -> Path:
    """CSV folder: OUTPUT_DIR from .env if set, otherwise the mode's default."""
    return project_path(setting) if setting.strip() else DEFAULT_OUTPUT_DIR


def resource_path(value: str) -> Path:
    """Read-only file: a user copy in APP_DIR wins, otherwise the bundled one."""
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    user_copy = APP_DIR / path
    return user_copy if user_copy.exists() else RESOURCE_DIR / path
