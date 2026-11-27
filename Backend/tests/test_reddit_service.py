from datetime import UTC, date, datetime

import pytest
from sentiboard_ml.reddit_index import write_index
from sqlalchemy import select

from app.config import settings
from app.models.post import Post, PostSource
from app.models.query import QueryStatus, SearchQuery
from app.services import jobs, reddit
from tests.test_keyword_job import (
    FakePredictor,
    create_keyword_query,
    make_session_factory,
)

POSTS = [
    ("The camera on this phone is amazing", "apple", "post", date(2025, 7, 31)),
    ("Camera app keeps crashing, so annoying", "android", "comment", date(2025, 7, 20)),
    ("Old camera review from June", "photography", "post", date(2025, 6, 9)),
    ("Nothing to see here", "misc", "post", date(2025, 7, 31)),
]


@pytest.fixture
def index_path(tmp_path, monkeypatch):
    path = tmp_path / "reddit_posts.sqlite"
    write_index(
        path,
        [
            {"text": t, "subreddit": s, "kind": k, "post_date": d}
            for t, s, k, d in POSTS
        ],
        {"source": "test"},
    )
    monkeypatch.setattr(settings, "reddit_index_path", str(path))
    return path


def test_fetch_posts_returns_reddit_posts(index_path):
    posts = reddit.fetch_posts("camera", 10, "all")

    assert len(posts) == 3
    first = next(p for p in posts if p["subreddit"] == "apple")
    assert first["text"] == "The camera on this phone is amazing"
    assert first["post_date"] == datetime(2025, 7, 31, tzinfo=UTC)
    assert first["external_id"].startswith("rd_")
    assert len(first["external_id"]) <= 50
    assert (first["author"], first["url"], first["score"]) == (None, None, None)


@pytest.mark.parametrize(
    ("time_range", "expected"),
    [("day", 1), ("week", 1), ("month", 2), ("year", 3), ("all", 3)],
)
def test_time_range_counts_back_from_newest_post(index_path, time_range, expected):
    assert len(reddit.fetch_posts("camera", 10, time_range)) == expected


def test_since_date():
    latest = date(2025, 7, 31)
    assert reddit.since_date(latest, "day") == latest
    assert reddit.since_date(latest, "week") == date(2025, 7, 25)
    assert reddit.since_date(latest, "all") is None
    assert reddit.since_date(None, "week") is None
    with pytest.raises(ValueError, match="Unknown time_range"):
        reddit.since_date(latest, "decade")


def test_limit_and_no_match(index_path):
    assert len(reddit.fetch_posts("camera", 2, "all")) == 2
    assert reddit.fetch_posts("bicycle", 10, "all") == []


def test_missing_index_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "reddit_index_path", str(tmp_path / "nope.sqlite"))
    with pytest.raises(FileNotFoundError, match="Reddit index not found"):
        reddit.fetch_posts("camera", 10, "all")


def test_keyword_job_uses_the_dataset(index_path, db, db_connection, monkeypatch):
    # create_keyword_query searches "camera" with time_range="month".
    query = create_keyword_query(db)
    query_id = query.query_id
    db.commit()
    monkeypatch.setattr(jobs, "clean_text", lambda text: text.lower())
    monkeypatch.setattr(jobs, "get_predictor", lambda _: FakePredictor())

    jobs.run_keyword_job(query_id, session_factory=make_session_factory(db_connection))

    db.expire_all()
    query = db.get(SearchQuery, query_id)
    assert query.status == QueryStatus.done, query.error_message
    assert query.post_count == 2
    posts = db.scalars(select(Post).where(Post.source == PostSource.reddit)).all()
    assert {p.subreddit for p in posts} == {"apple", "android"}
