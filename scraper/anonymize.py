"""Anonymization helpers.

Rules:
- @mentions (Twitter and Ekşi)            -> @username
- (bkz: @nick) / (ara: @nick) on Ekşi       -> (bkz: @username)
- bare occurrences of known usernames or
  display names seen during the run        -> #username
- profile / status links on x.com, twitter.com,
  eksisozluk.com/biri/...                  -> generic link
- e-mail addresses and phone numbers       -> [email] / [phone]
- post ids are never written; a salted HMAC (`post_hash`) is written
  instead so you can de-duplicate without being able to look the post up.
"""

from __future__ import annotations

import hashlib
import hmac
import html
import re
from collections.abc import Iterable

MENTION_TOKEN = "@username"
NAME_TOKEN = "#username"

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{8,}\d(?!\w)")
_EKSI_REF_RE = re.compile(r"\((bkz|ara|u)\s*:\s*@[^)]*\)", re.IGNORECASE)
_MENTION_RE = re.compile(r"(?<![\w@])@\w+")
_X_URL_RE = re.compile(
    r"https?://(?:www\.|mobile\.)?(?:x|twitter)\.com/(?!i/|hashtag/|search|home|intent/)\w+\S*",
    re.IGNORECASE,
)
_EKSI_USER_URL_RE = re.compile(r"https?://(?:www\.)?eksisozluk\.com/biri/\S+", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")

MIN_USERNAME_LEN = 3
MIN_DISPLAYNAME_LEN = 4


def clean_markup(text: str) -> str:
    """Strip simple HTML tags/entities that some APIs return."""
    return html.unescape(_HTML_TAG_RE.sub("", text or ""))


def _names_pattern(names: Iterable[str]) -> re.Pattern[str] | None:
    usable = sorted(
        {n.strip() for n in names if n and len(n.strip()) >= MIN_USERNAME_LEN},
        key=len,
        reverse=True,  # longest first so "ali veli" wins over "ali"
    )
    if not usable:
        return None
    alternation = "|".join(re.escape(n) for n in usable)
    return re.compile(rf"(?<![\w@#])(?:{alternation})(?!\w)", re.IGNORECASE)


def anonymize_text(text: str, known_names: Iterable[str] = ()) -> str:
    text = clean_markup(text)
    text = _X_URL_RE.sub("https://x.com/username", text)
    text = _EKSI_USER_URL_RE.sub("https://eksisozluk.com/biri/username", text)
    text = _EMAIL_RE.sub("[email]", text)  # before mentions, so foo@bar.com isn't a mention
    text = _EKSI_REF_RE.sub(lambda m: f"({m.group(1).lower()}: {MENTION_TOKEN})", text)
    text = _MENTION_RE.sub(MENTION_TOKEN, text)
    pattern = _names_pattern(known_names)
    if pattern:
        text = pattern.sub(NAME_TOKEN, text)
    text = _PHONE_RE.sub("[phone]", text)
    return text


_OPERATOR_RE = re.compile(r"\b(from|to|list|url):\S+", re.IGNORECASE)


def anonymize_query(query: str, known_names: Iterable[str] = ()) -> str:
    """Search queries can name accounts too (from:someone, @someone)."""
    query = _OPERATOR_RE.sub(lambda m: f"{m.group(1).lower()}:username", query)
    return anonymize_text(query, known_names)


def post_hash(source: str, raw_id: str, salt: bytes) -> str:
    return hmac.new(salt, f"{source}:{raw_id}".encode(), hashlib.sha256).hexdigest()[:16]
