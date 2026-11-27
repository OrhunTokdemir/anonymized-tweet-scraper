"""Edit .env: Twitter accounts and plain settings (used by the app's Accounts & settings tab).

This is the only code that writes .env. It edits TW_ACCOUNT_<n>_* lines (and
single settings such as OUTPUT_DIR) in place and leaves every other line
(comments, other settings) untouched.
Standard library only.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path

PLACEHOLDER_USERNAMES = {"", "your_twitter_username"}
_KEY_RE = re.compile(r"^TW_ACCOUNT_(\d+)_([A-Z_]+)=(.*)$")
_HANDLE_RE = re.compile(r"^[A-Za-z0-9_]{1,50}$")
_AUTH_TOKEN_RE = re.compile(r"^[0-9a-fA-F]{20,}$")
_CT0_RE = re.compile(r"^[0-9A-Za-z]{32,}$")


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def clean_username(raw: str) -> str:
    """Accept 'name', '@name' or a profile URL."""
    raw = raw.strip()
    raw = re.sub(r"^https?://(www\.)?(x|twitter)\.com/", "", raw, flags=re.IGNORECASE)
    return raw.lstrip("@").split("/")[0].split("?")[0]


def validate(username: str, auth_token: str, ct0: str, proxy: str = "") -> str:
    """-> cleaned username, or ValueError with a readable message."""
    name = clean_username(username)
    if not _HANDLE_RE.match(name):
        raise ValueError("Username: letters, digits and _ only (no @, no spaces).")
    if not _AUTH_TOKEN_RE.match(auth_token.strip()):
        raise ValueError("auth_token looks wrong: it should be a long hex value (about 40 characters).")
    if not _CT0_RE.match(ct0.strip()):
        raise ValueError("ct0 looks wrong: it should be a long value of letters/digits (usually 160 characters).")
    if proxy and re.search(r"\s", proxy.strip()):
        raise ValueError("Proxy must not contain spaces, e.g. http://user:pass@host:8080")
    return name


def ensure_env(path: Path, example: Path) -> None:
    if not path.exists():
        if example.exists():
            shutil.copyfile(example, path)
        else:
            path.write_text("", encoding="utf-8")
        os.chmod(path, 0o600)


def _read(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def _write(path: Path, lines: list[str]) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".env.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _slots(lines: list[str]) -> dict[int, dict[str, int]]:
    """{n: {FIELD: line_index}}"""
    slots: dict[int, dict[str, int]] = {}
    for i, line in enumerate(lines):
        if m := _KEY_RE.match(line.strip()):
            slots.setdefault(int(m.group(1)), {})[m.group(2)] = i
    return slots


def _value(lines: list[str], index: int) -> str:
    return _unquote(lines[index].split("=", 1)[1])


def _username(lines: list[str], fields: dict[str, int]) -> str:
    return _value(lines, fields["USERNAME"]) if "USERNAME" in fields else ""


def list_usernames(path: Path) -> list[str]:
    lines = _read(path)
    slots = _slots(lines)
    return [u for n in sorted(slots) if (u := _username(lines, slots[n])) not in PLACEHOLDER_USERNAMES]


def _find(lines: list[str], slots: dict[int, dict[str, int]], username: str) -> int | None:
    for n in sorted(slots):
        if _username(lines, slots[n]).lower() == username.lower():
            return n
    return None


def upsert_account(path: Path, username: str, auth_token: str, ct0: str, proxy: str = "") -> str:
    """Add or update an account. -> 'added' or 'updated'."""
    lines = _read(path)
    slots = _slots(lines)
    cookies = f'"auth_token={auth_token.strip()}; ct0={ct0.strip()}"'
    proxy = proxy.strip()

    n = _find(lines, slots, username)
    action = "updated" if n is not None else "added"
    if n is None:
        n = next((k for k in sorted(slots) if _username(lines, slots[k]) in PLACEHOLDER_USERNAMES), None)

    if n is None:  # append a fresh block after the last account line
        n = max(slots, default=0) + 1
        last = max((i for f in slots.values() for i in f.values()), default=len(lines) - 1)
        block = [f"TW_ACCOUNT_{n}_USERNAME={username}", f"TW_ACCOUNT_{n}_COOKIES={cookies}",
                 f"TW_ACCOUNT_{n}_PROXY={proxy}"]
        lines[last + 1:last + 1] = ([""] if slots else []) + block
        _write(path, lines)
        return action

    fields = slots[n]
    new_values = {"USERNAME": username, "COOKIES": cookies}
    if proxy or action == "added":
        new_values["PROXY"] = proxy  # empty proxy on update keeps the old one
    insert_at = max(fields.values()) + 1
    for field, value in new_values.items():
        line = f"TW_ACCOUNT_{n}_{field}={value}"
        if field in fields:
            lines[fields[field]] = line
        else:
            lines.insert(insert_at, line)
            insert_at += 1
    _write(path, lines)
    return action


_SETTING_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _setting_index(lines: list[str], key: str) -> int | None:
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    return next((i for i, line in enumerate(lines) if pattern.match(line)), None)


def _check_setting_key(key: str) -> None:
    if not _SETTING_KEY_RE.match(key) or key.startswith("TW_ACCOUNT_"):
        raise ValueError(f"Not a plain setting name: {key!r}")


def set_setting(path: Path, key: str, value: str) -> None:
    """Set KEY=value (a plain setting such as OUTPUT_DIR, never an account key).
    Replaces the existing line or appends one; everything else stays as it is."""
    _check_setting_key(key)
    if "\n" in value or "\r" in value:
        raise ValueError("A setting value must be a single line.")
    lines = _read(path)
    quoted = f'"{value}"' if (" " in value or "#" in value) and '"' not in value else value
    line = f"{key}={quoted}"
    i = _setting_index(lines, key)
    if i is None:
        lines.append(line)
    else:
        lines[i] = line
    _write(path, lines)


def unset_setting(path: Path, key: str) -> bool:
    """Remove KEY=... so the default applies again. -> whether a line was removed."""
    _check_setting_key(key)
    lines = _read(path)
    i = _setting_index(lines, key)
    if i is None:
        return False
    del lines[i]
    _write(path, lines)
    return True


def remove_account(path: Path, username: str) -> bool:
    """Remove the account and renumber later blocks so numbering stays continuous."""
    lines = _read(path)
    slots = _slots(lines)
    n = _find(lines, slots, username)
    if n is None:
        return False
    drop = set(slots[n].values())
    out: list[str] = []
    for i, line in enumerate(lines):
        if i in drop:
            continue
        m = _KEY_RE.match(line.strip())
        if m and int(m.group(1)) > n:
            line = f"TW_ACCOUNT_{int(m.group(1)) - 1}_{m.group(2)}={m.group(3)}"
        out.append(line)
    _write(path, out)
    return True
