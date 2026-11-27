from datetime import date

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from build_reddit_index import build, keep_text, to_post
from sentiboard_ml.reddit_index import read_meta, search

GOOD = "I really love the new camera on this phone, photos look great"


@pytest.mark.parametrize(
    "text",
    [
        "[deleted]",
        "too short text",
        "x" * 1001,
        "Look https://example.com/a-very-long-link-to-something-else ok",
        "I am a bot, and this action was performed automatically. Contact mods.",
        "Это полностью русский текст, его мы не берём в английский индекс",
    ],
)
def test_keep_text_drops_junk(text):
    assert keep_text(text) is None


def test_keep_text_normalises_spaces():
    assert keep_text(f"  {GOOD}\n\n ") == GOOD


def test_to_post():
    row = {"text": GOOD, "dataType": "comment", "communityName": "r/Android",
           "datetime": "2025-07-31"}  # fmt: skip
    assert to_post(row) == {
        "text": GOOD,
        "subreddit": "Android",
        "kind": "comment",
        "post_date": date(2025, 7, 31),
    }
    assert to_post({**row, "communityName": "r/NSFW_stuff"}) is None


def test_build_keeps_posts_samples_comments_and_dedups(tmp_path):
    rows = [
        {"text": f"Post number {i} about the camera on my phone", "dataType": "post",
         "communityName": "r/apple", "datetime": "2025-07-30"}
        for i in range(3)
    ] + [
        {"text": f"Comment number {i} about the camera on my phone", "dataType": "comment",
         "communityName": "r/apple", "datetime": "2025-07-31"}
        for i in range(10)
    ]  # fmt: skip
    rows.append(dict(rows[0]))  # duplicate post
    pq.write_table(pa.Table.from_pylist(rows), tmp_path / "chunk_0.parquet")
    out = tmp_path / "reddit.sqlite"

    stats = build([tmp_path / "chunk_0.parquet"], out, max_rows=6, seed=1)

    assert (stats["kept_posts"], stats["kept_comments"]) == (3, 3)
    meta = read_meta(out)
    assert meta["rows"] == 6
    assert meta["rows_read"] == 14
    assert len(search(out, "camera", 100)) == 6
