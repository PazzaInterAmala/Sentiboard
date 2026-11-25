"""Offline Reddit search: a SQLite file with an FTS5 full-text index over Reddit posts.

The live Reddit API is closed to new apps, so keyword search runs over a downloaded
dataset instead. `ML/build_reddit_index.py` builds the file once; the backend opens it
read-only and calls `search()`. Only the standard library is needed at runtime.

File layout:
    posts(rowid, external_id, text, subreddit, kind, post_date 'YYYY-MM-DD')
    posts_fts   FTS5 index over posts.text (porter stemming: "phones" matches "phone")
    meta(key, value)   source dataset, row count, min_date / max_date
"""

import hashlib
import json
import os
import re
import sqlite3
from collections.abc import Iterable
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import TypedDict

SCHEMA = """
CREATE TABLE posts (
    rowid INTEGER PRIMARY KEY,
    external_id TEXT NOT NULL UNIQUE,
    text TEXT NOT NULL,
    subreddit TEXT,
    kind TEXT,
    post_date TEXT
);
CREATE INDEX posts_post_date ON posts (post_date);
CREATE VIRTUAL TABLE posts_fts USING fts5(
    text, content='posts', content_rowid='rowid', tokenize='porter unicode61'
);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

_WORD = re.compile(r"\w+")


class IndexPost(TypedDict):
    text: str
    subreddit: str | None
    kind: str | None  # "post" or "comment"
    post_date: date | None


class FoundPost(TypedDict):
    external_id: str
    text: str
    subreddit: str | None
    kind: str | None
    post_date: date | None


def make_external_id(post: IndexPost) -> str:
    """Stable id for a post (the dataset has none): same post -> same id on every rebuild."""
    key = "\x1f".join([post["text"], post["subreddit"] or "", str(post["post_date"] or "")])
    return "rd_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]


def write_index(path: str | Path, posts: Iterable[IndexPost], meta: dict) -> int:
    """Write posts into a new index file at `path` (replaced atomically). Returns row count.

    Posts with the same external_id (same text, subreddit and date) are stored once.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.unlink(missing_ok=True)

    con = sqlite3.connect(tmp)
    try:
        con.executescript(SCHEMA)
        con.executemany(
            "INSERT OR IGNORE INTO posts (external_id, text, subreddit, kind, post_date)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                (
                    make_external_id(p),
                    p["text"],
                    p["subreddit"],
                    p["kind"],
                    p["post_date"].isoformat() if p["post_date"] else None,
                )
                for p in posts
            ),
        )
        con.execute("INSERT INTO posts_fts (posts_fts) VALUES ('rebuild')")
        count, min_date, max_date = con.execute(
            "SELECT count(*), min(post_date), max(post_date) FROM posts"
        ).fetchone()
        full_meta = {**meta, "rows": count, "min_date": min_date, "max_date": max_date}
        con.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            ((k, json.dumps(v)) for k, v in full_meta.items()),
        )
        con.commit()
        con.execute("VACUUM")
    finally:
        con.close()
    os.replace(tmp, path)
    return count


def read_meta(path: str | Path) -> dict:
    # closing(): sqlite3's own context manager only commits, it does not close the file.
    with closing(_connect(path)) as con:
        return {k: json.loads(v) for k, v in con.execute("SELECT key, value FROM meta")}


def latest_date(path: str | Path) -> date | None:
    """Newest post date in the index: time ranges are counted back from it, not from today."""
    max_date = read_meta(path).get("max_date")
    return date.fromisoformat(max_date) if max_date else None


def search(
    path: str | Path, keyword: str, limit: int, since: date | None = None
) -> list[FoundPost]:
    """Posts containing every word of `keyword`: first those with the exact phrase
    ("remote work" side by side), then the rest; best matches first within each group.

    `since` keeps only posts dated on or after that day. A keyword with no word
    characters finds nothing.
    """
    words = to_words(keyword)
    if not words or limit <= 0:
        return []
    phrase = '"' + " ".join(words) + '"'
    all_words = " ".join(f'"{word}"' for word in words)

    rows: dict[str, tuple] = {}
    with closing(_connect(path)) as con:
        for query in dict.fromkeys([phrase, all_words]):  # one query for a single word
            if len(rows) >= limit:
                break
            for row in con.execute(_SEARCH_SQL, (query, _iso(since), _iso(since), limit)):
                rows.setdefault(row[0], row)
    return [
        FoundPost(
            external_id=external_id,
            text=text,
            subreddit=subreddit,
            kind=kind,
            post_date=date.fromisoformat(post_date) if post_date else None,
        )
        for external_id, text, subreddit, kind, post_date in list(rows.values())[:limit]
    ]


_SEARCH_SQL = """
    SELECT p.external_id, p.text, p.subreddit, p.kind, p.post_date
    FROM posts_fts JOIN posts p ON p.rowid = posts_fts.rowid
    WHERE posts_fts MATCH ? AND (? IS NULL OR p.post_date >= ?)
    ORDER BY posts_fts.rank
    LIMIT ?
"""


def to_words(keyword: str) -> list[str]:
    """Words of the keyword, lowercased. Only word characters are kept and each word is
    quoted in the FTS5 query, so operators typed by the user (OR, NOT, *, quotes) are
    matched as plain words."""
    return _WORD.findall(keyword.lower())


def _connect(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Reddit index not found: {path}")
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None
