"""Keyword search over the downloaded Reddit dataset (used by the keyword job).

The live Reddit API is closed to new apps, so posts come from an offline index built by
ML/build_reddit_index.py (see ML/README.md) and stored at REDDIT_INDEX_PATH.

The dataset covers a fixed period, so time ranges count back from its newest post, not
from today: "week" means the last 7 days of the dataset.
"""

from datetime import UTC, date, datetime, time, timedelta

from sentiboard_ml import reddit_index

from app.config import settings
from app.services.jobs import RedditPost

TIME_RANGE_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}


def fetch_posts(keyword: str, limit: int, time_range: str) -> list[RedditPost]:
    """Posts that contain every word of `keyword`, best matches first, at most `limit`."""
    path = settings.reddit_index_path
    since = since_date(reddit_index.latest_date(path), time_range)
    return [
        RedditPost(
            external_id=post["external_id"],
            text=post["text"],
            subreddit=post["subreddit"],
            author=None,  # the dataset only has encoded usernames and links
            url=None,
            score=None,
            post_date=_to_datetime(post["post_date"]),
        )
        for post in reddit_index.search(path, keyword, limit, since)
    ]


def since_date(latest: date | None, time_range: str) -> date | None:
    """First day included by `time_range`, counting back from the dataset's newest day."""
    if time_range == "all" or latest is None:
        return None
    if time_range not in TIME_RANGE_DAYS:
        raise ValueError(f"Unknown time_range: {time_range}")
    return latest - timedelta(days=TIME_RANGE_DAYS[time_range] - 1)


def _to_datetime(day: date | None) -> datetime | None:
    return datetime.combine(day, time(), tzinfo=UTC) if day else None
