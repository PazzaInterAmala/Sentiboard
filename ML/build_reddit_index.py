"""Build the offline Reddit search index used by the backend's keyword search.

The live Reddit API is closed to new apps, so SentiBoard searches a downloaded dataset:
goldentraversy07/reddit_dataset_202507 on Hugging Face (MIT license; Reddit posts and
comments from thousands of subreddits, June-July 2025).

    # download some parquet files from the dataset's data/ folder, e.g. chunk_0 and 12-29
    python build_reddit_index.py path/to/parquet_dir --out artifacts/reddit_posts.sqlite

Keeps English-looking texts of 30-1000 characters, drops bots, removed posts, duplicates
and NSFW subreddits, then keeps every post and a random sample of comments up to
--max-rows. Needs pyarrow (`pip install -e ".[train]"`).
"""

import argparse
import hashlib
import random
import re
from datetime import UTC, date, datetime
from pathlib import Path

import pyarrow.parquet as pq

from sentiboard_ml.reddit_index import IndexPost, write_index

DATASET = "goldentraversy07/reddit_dataset_202507"
COLUMNS = ["text", "dataType", "communityName", "datetime"]

MIN_CHARS, MAX_CHARS, MIN_WORDS = 30, 1000, 5
MIN_ASCII_LETTER_SHARE = 0.9  # cheap "is it English" check

DROP_TEXTS = {"[deleted]", "[removed]"}
BOT_MARKERS = ("i am a bot", "i'm a bot", "this action was performed automatically")
NSFW_SUBREDDIT = re.compile(
    r"nsfw|porn|gonewild|onlyfans|hentai|nude|boob|r4r|sex|cumsluts|lewd|xxx", re.IGNORECASE
)
URL = re.compile(r"https?://\S+")
SPACES = re.compile(r"\s+")


def keep_text(text: str) -> str | None:
    """Normalised text if it is worth indexing, else None."""
    text = SPACES.sub(" ", text or "").strip()
    if text in DROP_TEXTS or not MIN_CHARS <= len(text) <= MAX_CHARS:
        return None
    lower = text.lower()
    if any(marker in lower for marker in BOT_MARKERS):
        return None
    without_urls = URL.sub("", text)
    if len(without_urls.split()) < MIN_WORDS:
        return None
    letters = [c for c in without_urls if c.isalpha()]
    if not letters:
        return None
    ascii_letters = sum(c.isascii() for c in letters)
    if ascii_letters / len(letters) < MIN_ASCII_LETTER_SHARE:
        return None
    return text


def read_rows(files: list[Path]):
    for file in files:  # in batches: one parquet file can hold ~1M rows
        for batch in pq.ParquetFile(file).iter_batches(columns=COLUMNS, batch_size=50_000):
            yield from batch.to_pylist()


def to_post(row: dict) -> IndexPost | None:
    subreddit = (row.get("communityName") or "").removeprefix("r/") or None
    if subreddit and NSFW_SUBREDDIT.search(subreddit):
        return None
    text = keep_text(row.get("text"))
    if text is None:
        return None
    return IndexPost(
        text=text,
        subreddit=subreddit,
        kind=row.get("dataType"),
        post_date=_parse_date(row.get("datetime")),
    )


def build(files: list[Path], out: Path, max_rows: int, seed: int) -> dict:
    """Keep every post and a uniform random sample of comments (reservoir sampling, so
    memory stays at ~max_rows texts however many rows the files have)."""
    rng = random.Random(seed)
    posts, comments, seen = [], [], set()
    total = comments_seen = 0
    for row in read_rows(files):
        total += 1
        post = to_post(row)
        if post is None:
            continue
        key = hashlib.sha1(post["text"].lower().encode("utf-8")).digest()
        if key in seen:
            continue
        seen.add(key)
        if post["kind"] == "post":
            posts.append(post)
            continue
        comments_seen += 1
        if len(comments) < max_rows:
            comments.append(post)
        elif (slot := rng.randrange(comments_seen)) < max_rows:
            comments[slot] = post

    rng.shuffle(posts)
    rng.shuffle(comments)  # reservoir slots are not in random order
    posts = posts[:max_rows]
    comments = comments[: max_rows - len(posts)]

    stats = {
        "source": f"https://huggingface.co/datasets/{DATASET}",
        "files": sorted(f.name for f in files),
        "rows_read": total,
        "kept_posts": len(posts),
        "kept_comments": len(comments),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": seed,
    }
    write_index(out, posts + comments, stats)
    return stats


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path, help="parquet file or folder of parquet files")
    parser.add_argument("--out", type=Path, default=Path("artifacts/reddit_posts.sqlite"))
    parser.add_argument("--max-rows", type=int, default=200_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    files = sorted(args.input.glob("*.parquet")) if args.input.is_dir() else [args.input]
    if not files:
        parser.error(f"no parquet files in {args.input}")
    stats = build(files, args.out, args.max_rows, args.seed)
    size_mb = args.out.stat().st_size / 1e6
    print(f"{args.out}: {stats['kept_posts']} posts + {stats['kept_comments']} comments "
          f"from {stats['rows_read']} rows, {size_mb:.0f} MB")  # fmt: skip


if __name__ == "__main__":
    main()
