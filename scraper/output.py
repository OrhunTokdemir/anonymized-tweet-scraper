"""CSV writing and file naming.

Naming format:  <output_dir>/YYYYMMDD-HHMMSS[_<prefix>]_tw<N>_eksi<M>_<slug>.csv
  e.g.          data/20261115-143002_tw10_eksi2_yapay-zeka.csv
                data/20261115-150510_offensive_tw100_eksi40_tr-offensive.csv

- timestamp first  -> files sort chronologically in `ls`
- tw/eksi counts   -> the actual number of rows from each source
- slug             -> ASCII version of the (anonymized) search terms, max 40 chars
"""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

from .anonymize import anonymize_query, anonymize_text
from .models import CSV_COLUMNS, Post

_TR = str.maketrans("çğıöşüÇĞİÖŞÜâîû", "cgiosuCGIOSUaiu")


def slugify(*parts: str, max_len: int = 40) -> str:
    text = " ".join(p for p in parts if p).translate(_TR).lower()
    text = re.sub(r"(https?://)?\S*eksisozluk\.com/", "", text)
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return slug[:max_len].rstrip("-") or "posts"


def build_filename(
    output_dir: str, n_tw: int, n_eksi: int, *terms: str, prefix: str = ""
) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    prefix = f"_{prefix}" if prefix else ""
    slug = slugify(*(anonymize_query(t) for t in terms))
    return Path(output_dir) / f"{stamp}{prefix}_tw{n_tw}_eksi{n_eksi}_{slug}.csv"


def write_csv(posts: list[Post], path: Path) -> None:
    # Redact every username/display name seen anywhere in this run, so
    # cross-references between posts are caught too.
    known_names: set[str] = set()
    for p in posts:
        known_names |= p.names

    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig so Excel/LibreOffice open Turkish characters correctly
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for i, p in enumerate(posts, start=1):
            writer.writerow(
                {
                    "row": i,
                    "source": p.source,
                    "method": p.method,
                    "query": anonymize_query(p.query, known_names),
                    "topic": p.topic,
                    "text": anonymize_text(p.text, known_names),
                    "created_at": p.created_at,
                    "lang": p.lang,
                    "like_count": p.like_count,
                    "repost_count": p.repost_count,
                    "reply_count": p.reply_count,
                    "quote_count": p.quote_count,
                    "view_count": p.view_count,
                    "favorite_count": p.favorite_count,
                    "hashtags": p.hashtags,
                    "post_type": p.post_type,
                    "sample_group": p.sample_group,
                    "matched_terms": p.matched_terms,
                    "matched_categories": p.matched_categories,
                }
            )
