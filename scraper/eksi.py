"""Ekşi Sözlük scraping through Ekşi's own mobile API (via the `eksiapi` client).

Ekşi does not publish public API docs. `eksiapi` talks to the same
api.eksisozluk.com endpoints the Android app uses, with an anonymous token, so
no Ekşi account is needed.
"""

from __future__ import annotations

import random
import re
import time
from collections.abc import Callable, Mapping
from typing import Any, Literal

from eksiapi import EksiClient
from eksiapi.errors import EksiApiError

from .config import Settings
from .models import Post

Order = Literal["chronological", "popular", "today"]
Progress = Callable[[str], None]

EKSI_METHODS = {
    "topic": "One topic (başlık)",
    "search": "Keyword search over titles",
    "gundem": "Gündem (popular now)",
}
EKSI_ORDERS = {
    "popular": "Most-liked first",
    "chronological": "Oldest first",
    "today": "Today's entries",
}
_ACTION: dict[str, Literal["popular", "today"] | None] = {
    "chronological": None,
    "popular": "popular",
    "today": "today",
}
_TOPIC_ID_IN_URL = re.compile(r"--(\d+)(?:[/?#]|$)")


def _pick(data: Mapping[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def _pause() -> None:
    time.sleep(random.uniform(0.5, 1.5))


def _resolve_topic(client: EksiClient, term: str) -> int:
    if term.isdigit():
        return int(term)
    if m := _TOPIC_ID_IN_URL.search(term):
        return int(m.group(1))
    return client.resolve_topic_id(term)


def _entries_from_topic(
    client: EksiClient, topic_id: int, limit: int, order: Order, method: str, query: str
) -> list[Post]:
    posts: list[Post] = []
    page = 1
    while len(posts) < limit:
        topic = client.topic_typed(topic_id, page, action=_ACTION[order])
        if not topic.entries:
            break
        for entry in topic.entries:
            if not entry.content:
                continue
            posts.append(
                Post(
                    source="eksisozluk",
                    method=f"{method}-{order}",
                    query=query,
                    topic=topic.title or "",
                    text=entry.content,
                    raw_id=str(entry.id or ""),
                    created_at=str(entry.created_at or ""),
                    favorite_count=_pick(entry.raw, "FavoriteCount", "favoriteCount"),
                    names={entry.author} if entry.author else set(),
                )
            )
            if len(posts) >= limit:
                break
        if topic.page_count is None or page >= topic.page_count:
            break
        page += 1
        _pause()
    return posts


def _topic_ids(items: Any) -> list[int]:
    ids = []
    for item in items:
        if isinstance(item, Mapping):
            value = _pick(item, "TopicId", "topicId", "Id", "id", default=None)
            if value is not None and str(value).isdigit():
                ids.append(int(value))
    return ids


def _spread(
    client: EksiClient, topic_ids: list[int], limit: int, order: Order, method: str,
    query: str, per_topic: int, progress: Progress,
) -> list[Post]:
    posts: list[Post] = []
    for topic_id in topic_ids:
        if len(posts) >= limit:
            break
        take = min(per_topic, limit - len(posts))
        try:
            got = _entries_from_topic(client, topic_id, take, order, method, query)
            if not got and order == "today":  # topic may have no entries today
                got = _entries_from_topic(client, topic_id, take, "chronological", method, query)
        except EksiApiError as exc:
            progress(f"Ekşi: skipping topic {topic_id} ({exc.__class__.__name__})")
            continue
        posts.extend(got)
        progress(f"Ekşi: {len(posts)}/{limit}")
        _pause()
    return posts


def fetch_eksi(
    method: str, query: str, limit: int, order: Order, settings: Settings, progress: Progress,
    per_topic: int | None = None,
) -> list[Post]:
    """method: 'topic' (one başlık), 'search' (keyword over titles), 'gundem' (popular now)."""
    per_topic = per_topic or settings.eksi_max_per_topic
    with EksiClient.anonymous(raw_response=False) as client:
        if method == "topic":
            topic_id = _resolve_topic(client, query)
            posts = _entries_from_topic(client, topic_id, limit, order, method, query)
            progress(f"Ekşi: {len(posts)}/{limit}")
            return posts

        if method == "search":
            page = client.page(client.search_topics(query))
            ids = _topic_ids(page.items)
            if not ids:
                progress("Ekşi: no topics matched that keyword.")
            return _spread(client, ids, limit, order, method, query, per_topic, progress)

        if method == "gundem":
            ids: list[int] = []
            for p in (1, 2):
                ids += _topic_ids(client.page(client.popular(page=p)).items)
            return _spread(client, ids, limit, order, method, "gündem", per_topic, progress)

    raise ValueError(f"Unknown Ekşi method: {method}")
