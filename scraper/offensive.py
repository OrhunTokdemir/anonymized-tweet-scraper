"""Offensive-language batch: a Turkish dataset mixing offensive candidates and controls.

The labels produced here are WEAK labels (lexicon hits). They are meant as a
starting pool for human annotation, not as ground truth.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .anonymize import anonymize_text
from .models import Post
from .paths import resource_path

Progress = Callable[[str], None]

OFFENSIVE = "offensive_candidate"
CONTROL = "control"

X_QUERY_MAX = 450  # X rejects very long queries; stay well under ~512 chars
BASE_FILTER = "lang:tr -filter:retweets"
CONTROL_WORDS = ["ve", "bir", "bu", "çok", "ama", "için", "ne"]

_LEET = str.maketrans({"1": "i", "3": "e", "0": "o", "4": "a", "5": "s", "7": "t", "$": "s", "€": "e"})
_PLACEHOLDERS = re.compile(r"https?://\S+|[@#]username|\[(?:email|phone)\]")
_SPACED_LETTERS = re.compile(r"(?<!\w)(?:\w[.\-_*\s]){1,}\w(?!\w)")
_REPEATS = re.compile(r"(\w)\1{2,}")


def normalize_tr(text: str) -> str:
    """Normalize Turkish text for matching (never used for output).

    - Turkish-aware lowercasing (I -> ı, İ -> i)
    - leetspeak (s1kt1r -> siktir, @ is handled after placeholders are removed)
    - spaced/dotted single letters joined (a.q -> aq, s i k -> sik)
    - 3+ repeated letters collapsed (siktirrrr -> siktir)
    """
    text = _PLACEHOLDERS.sub(" ", text)
    text = re.sub(r"['’`]", "", text)  # allah'ın -> allahın
    text = text.replace("I", "ı").replace("İ", "i").lower()
    text = text.translate(_LEET).replace("@", "a")
    text = _SPACED_LETTERS.sub(lambda m: re.sub(r"[.\-_*\s]", "", m.group()), text)
    text = _REPEATS.sub(r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Term:
    raw: str  # as written in the lexicon (used in X queries)
    norm: str  # normalized (used for local matching)
    category: str
    whole_word: bool
    pattern: re.Pattern[str] = field(repr=False, default=None)  # type: ignore[assignment]


@dataclass
class Lexicon:
    name: str
    terms: list[Term]

    def match(self, text: str) -> list[Term]:
        norm = normalize_tr(text)
        return [t for t in self.terms if t.pattern.search(norm)]


def load_lexicon(path: str | Path) -> Lexicon:
    """One term per line. `# category` starts a category. A trailing `$` means
    whole-word only (for short/ambiguous terms such as `aq$` or `göt$`).
    Without `$` a term also matches with Turkish suffixes (şerefsiz -> şerefsizler)."""
    path = resource_path(str(path))
    if not path.is_file():
        raise FileNotFoundError(f"Lexicon not found: {path}")
    category = "uncategorized"
    terms: list[Term] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            category = line.lstrip("#").strip() or category
            continue
        whole = line.endswith("$")
        raw = line.rstrip("$").strip()
        norm = normalize_tr(raw)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        tail = r"(?!\w)" if whole else ""
        terms.append(
            Term(raw, norm, category, whole, re.compile(rf"(?<!\w){re.escape(norm)}{tail}"))
        )
    if not terms:
        raise ValueError(f"Lexicon {path} has no terms.")
    return Lexicon(path.stem, terms)


def _quote(term: str) -> str:
    return f'"{term}"' if " " in term else term


def build_queries(terms: list[str], extra: str = "", max_len: int = X_QUERY_MAX) -> list[str]:
    """Split terms into `(a OR b OR ...) lang:tr -filter:retweets <extra>` queries under max_len."""
    suffix = f" {BASE_FILTER}" + (f" {extra.strip()}" if extra.strip() else "")
    queries: list[str] = []
    group: list[str] = []

    def render(g: list[str]) -> str:
        return f"({' OR '.join(g)}){suffix}"

    for term in (_quote(t) for t in terms):
        if group and len(render(group + [term])) > max_len:
            queries.append(render(group))
            group = []
        group.append(term)
    if group:
        queries.append(render(group))
    return queries


def build_control_query(terms: list[str], extra: str = "", max_len: int = X_QUERY_MAX) -> str:
    """Generic Turkish query that excludes as many lexicon terms as fit."""
    query = f"({' OR '.join(CONTROL_WORDS)}) {BASE_FILTER}"
    if extra.strip():
        query += f" {extra.strip()}"
    for term in terms:
        candidate = f"{query} -{_quote(term)}"
        if len(candidate) > max_len:
            break
        query = candidate
    return query


def split_counts(total: int, ratio_pct: int) -> tuple[int, int]:
    """-> (offensive, control)."""
    ratio_pct = max(0, min(100, ratio_pct))
    offensive = round(total * ratio_pct / 100)
    return offensive, total - offensive


def text_fingerprint(post: Post) -> str:
    return hashlib.sha1(normalize_tr(anonymize_text(post.text, post.names)).encode()).hexdigest()


def classify(posts: list[Post], lexicon: Lexicon) -> tuple[list[Post], list[Post]]:
    """Tag posts in place; -> (offensive_candidates, controls). Matching runs on anonymized text."""
    offensive, control = [], []
    for post in posts:
        hits = lexicon.match(anonymize_text(post.text, post.names))
        if hits:
            post.sample_group = OFFENSIVE
            post.matched_terms = "|".join(dict.fromkeys(t.raw for t in hits))
            post.matched_categories = "|".join(dict.fromkeys(t.category for t in hits))
            offensive.append(post)
        else:
            post.sample_group = CONTROL
            control.append(post)
    return offensive, control


def dedupe(posts: list[Post], seen: set[str]) -> list[Post]:
    out = []
    for post in posts:
        fp = text_fingerprint(post)
        if fp not in seen:
            seen.add(fp)
            out.append(post)
    return out


async def collect_twitter(
    api, lexicon: Lexicon, n_off: int, n_ctrl: int, extra: str, settings, progress: Progress,
    exclude_duplicates: bool = True,
) -> list[Post]:
    from .twitter import fetch_search

    seen_text: set[str] = set()
    seen_ids: set[str] = set()
    offensive: list[Post] = []
    control: list[Post] = []

    def absorb(batch: list[Post], label: str) -> tuple[list[Post], list[Post]]:
        # Short label instead of the long "(a OR b OR ...) lang:tr" search string;
        # the actual hits are in matched_terms.
        for p in batch:
            p.query = label
        batch = [p for p in batch if p.raw_id not in seen_ids]
        seen_ids.update(p.raw_id for p in batch)
        if exclude_duplicates:
            batch = dedupe(batch, seen_text)
        return classify(batch, lexicon)

    search_terms = [t.raw for t in lexicon.terms]
    if n_off > 0:
        queries = build_queries(search_terms, extra)
        # Spread over all queries so one term group doesn't dominate; over-fetch
        # a bit to make up for duplicates and posts the local matcher rejects.
        per_query = max(5, math.ceil(n_off * 1.3 / len(queries)))
        for i, q in enumerate(queries, 1):
            if len(offensive) >= n_off:
                break
            progress(f"Offensive query {i}/{len(queries)}")
            off, _ = absorb(await fetch_search(api, q, per_query, "Latest", settings, progress,
                                               method="offensive-search"), f"lexicon:{lexicon.name}")
            offensive.extend(off)  # posts the local matcher didn't confirm are dropped

    if n_ctrl > 0:
        progress("Control query")
        q = build_control_query(search_terms, extra)
        off, ctrl = absorb(await fetch_search(api, q, math.ceil(n_ctrl * 1.2) + 5, "Latest",
                                              settings, progress, method="control-search"), "control")
        offensive.extend(off)  # control posts that still contain lexicon words
        control.extend(ctrl)

    if len(offensive) < n_off:
        progress(f"Only {len(offensive)}/{n_off} offensive candidates found on Twitter.")
    if len(control) < n_ctrl:
        progress(f"Only {len(control)}/{n_ctrl} control tweets found.")
    return offensive[:n_off] + control[:n_ctrl]


def collect_eksi(
    lexicon: Lexicon, n_off: int, n_ctrl: int, settings, progress: Progress,
    exclude_duplicates: bool = True,
) -> list[Post]:
    """Scan gündem entries and split them by lexicon hits. Ekşi has no
    cross-site full-text search, so this samples what is being discussed now."""
    from .eksi import fetch_eksi

    scan = min(800, max(100, (n_off + n_ctrl) * 10))
    progress(f"Ekşi: scanning up to {scan} gündem entries...")
    entries = fetch_eksi("gundem", "", scan, "today", settings, progress, per_topic=15)
    if exclude_duplicates:
        entries = dedupe(entries, set())
    offensive, control = classify(entries, lexicon)
    for p in offensive + control:
        p.method = "offensive-gundem"
    if len(offensive) < n_off:
        progress(f"Only {len(offensive)}/{n_off} offensive candidates found on Ekşi.")
    return offensive[:n_off] + control[:n_ctrl]
