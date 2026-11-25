from datetime import date

import pytest

from sentiboard_ml.reddit_index import (
    latest_date,
    make_external_id,
    read_meta,
    search,
    to_words,
    write_index,
)


def post(text, subreddit="r/apple", kind="post", day=date(2025, 7, 20)):
    return {"text": text, "subreddit": subreddit, "kind": kind, "post_date": day}


POSTS = [
    post("The new iPhone camera is amazing", day=date(2025, 7, 30)),
    post("My old iphone battery died again", day=date(2025, 7, 1)),
    post("Remote work made me so much happier", "r/jobs", day=date(2025, 7, 29)),
    post("Back to the office, I miss remote work", "r/jobs", "comment", date(2025, 6, 9)),
    post("Phones are too expensive these days", "r/android", day=date(2025, 7, 31)),
]


@pytest.fixture
def index(tmp_path):
    path = tmp_path / "reddit.sqlite"
    write_index(path, POSTS, {"source": "test"})
    return path


def texts(found):
    return sorted(p["text"] for p in found)


def test_write_index_meta_and_dedup(tmp_path):
    path = tmp_path / "reddit.sqlite"
    count = write_index(path, POSTS + [POSTS[0]], {"source": "test"})

    assert count == len(POSTS)
    meta = read_meta(path)
    assert meta["source"] == "test"
    assert meta["rows"] == len(POSTS)
    assert (meta["min_date"], meta["max_date"]) == ("2025-06-09", "2025-07-31")
    assert latest_date(path) == date(2025, 7, 31)


def test_search_is_case_insensitive(index):
    assert texts(search(index, "IPHONE", 10)) == [
        "My old iphone battery died again",
        "The new iPhone camera is amazing",
    ]


def test_search_needs_every_word(index):
    found = search(index, "remote work", 10)
    assert {p["subreddit"] for p in found} == {"r/jobs"}
    assert len(found) == 2
    assert search(index, "remote iphone", 10) == []


def test_exact_phrase_comes_first(tmp_path):
    path = tmp_path / "reddit.sqlite"
    write_index(path, [
        post("Work from home is fine, the remote is lost"),
        post("I love remote work"),
    ], {})  # fmt: skip
    found = search(path, "remote work", 10)
    assert [p["text"] for p in found] == [
        "I love remote work",
        "Work from home is fine, the remote is lost",
    ]
    assert [p["text"] for p in search(path, "remote work", 1)] == ["I love remote work"]


def test_search_uses_stemming(index):
    assert texts(search(index, "phone", 10)) == ["Phones are too expensive these days"]


def test_search_since_and_limit(index):
    assert texts(search(index, "iphone", 10, since=date(2025, 7, 24))) == [
        "The new iPhone camera is amazing"
    ]
    assert len(search(index, "iphone", 1)) == 1
    assert search(index, "iphone", 0) == []


def test_search_returns_fields(index):
    [found] = search(index, "camera", 10)
    assert found == {
        "external_id": make_external_id(POSTS[0]),
        "text": "The new iPhone camera is amazing",
        "subreddit": "r/apple",
        "kind": "post",
        "post_date": date(2025, 7, 30),
    }


@pytest.mark.parametrize("keyword", ['iphone" OR "x', "iphone*", "NOT iphone", "(iphone"])
def test_fts_operators_are_plain_words(index, keyword):
    search(index, keyword, 10)  # must not raise an FTS5 syntax error


def test_keyword_without_words_finds_nothing(index):
    assert to_words("  !!! ") == []
    assert search(index, "!!!", 10) == []


def test_missing_index_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="Reddit index not found"):
        search(tmp_path / "nope.sqlite", "iphone", 10)


def test_external_id_is_stable_and_short():
    assert make_external_id(POSTS[0]) == make_external_id(dict(POSTS[0]))
    assert make_external_id(POSTS[0]) != make_external_id(POSTS[1])
    assert len(make_external_id(POSTS[0])) <= 50
