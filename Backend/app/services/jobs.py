import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import NotRequired, TypedDict

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.ml.registry import Predictor, clean_text, get_predictor
from app.models.post import Post, PostSource
from app.models.prediction import Prediction, SentimentLabel
from app.models.query import QueryPost, QueryStatus, QueryType, SearchQuery

logger = logging.getLogger(__name__)
PREDICTION_BATCH_SIZE = 32
MAX_ERROR_MESSAGE_LENGTH = 500
ALLOWED_TIME_RANGES = {"day", "week", "month", "year", "all"}

CsvRow = dict[str, str | None]
SessionFactory = Callable[[], Session]


class RedditPost(TypedDict):
    external_id: str
    text: str
    author: NotRequired[str | None]
    subreddit: NotRequired[str | None]
    url: NotRequired[str | None]
    score: NotRequired[int | None]
    post_date: NotRequired[datetime | None]


class RedditPostValues(TypedDict):
    external_id: str
    source: PostSource
    text: str
    clean_text: str
    author: str | None
    subreddit: str | None
    url: str | None
    score: int | None
    post_date: datetime | None


FetchPosts = Callable[[str, int, str], Sequence[RedditPost]]


def _parse_post_date(value: str | None) -> datetime | None:
    if value is None or not value.strip():
        return None

    date = datetime.fromisoformat(value.strip())
    if date.tzinfo is None:
        date = date.replace(tzinfo=UTC)
    return date


def _persist_predictions(
    db: Session,
    posts: Sequence[Post],
    model_id: int,
    predictor: Predictor,
) -> None:
    for start in range(0, len(posts), PREDICTION_BATCH_SIZE):
        batch = posts[start : start + PREDICTION_BATCH_SIZE]
        results = predictor.predict([post.clean_text or "" for post in batch])

        if len(results) != len(batch):
            raise ValueError("The predictor returned an unexpected number of results")

        for post, result in zip(batch, results, strict=True):
            probabilities = result.probabilities
            db.add(
                Prediction(
                    post_id=post.post_id,
                    model_id=model_id,
                    sentiment=SentimentLabel(result.label),
                    confidence=result.confidence,
                    prob_positive=probabilities["positive"],
                    prob_neutral=probabilities["neutral"],
                    prob_negative=probabilities["negative"],
                )
            )


def _mark_query_failed(
    query_id: int,
    error_message: str,
    session_factory: SessionFactory,
    job_name: str,
) -> None:
    with session_factory() as db:
        query = db.get(SearchQuery, query_id)
        if query is None:
            logger.error(
                "Cannot mark missing %s query %s as failed", job_name, query_id
            )
            return

        query.status = QueryStatus.failed
        query.error_message = error_message[:MAX_ERROR_MESSAGE_LENGTH]
        query.finished_at = datetime.now(UTC)
        db.commit()


def run_csv_job(
    query_id: int,
    rows: Sequence[CsvRow],
    *,
    skipped_rows: int = 0,
    session_factory: SessionFactory = SessionLocal,
) -> None:
    try:
        with session_factory() as db:
            query = db.get(SearchQuery, query_id)
            if query is None:
                raise LookupError(f"CSV query {query_id} was not found")
            if query.type != QueryType.csv:
                raise ValueError(f"Query {query_id} is not a CSV query")
            if query.status != QueryStatus.pending:
                raise ValueError(f"CSV query {query_id} is not pending")
            if query.model_id is None:
                raise LookupError(f"CSV query {query_id} has no model configured")

            model_id = query.model_id
            query.status = QueryStatus.processing
            query.error_message = None
            db.commit()

            posts: list[Post] = []
            skipped_invalid_dates = 0
            for row in rows:
                try:
                    post_date = _parse_post_date(row["date"])
                except ValueError:
                    skipped_invalid_dates += 1
                    continue

                text = row["text"]
                posts.append(
                    Post(
                        source=PostSource.csv,
                        text=text,
                        clean_text=clean_text(text),
                        post_date=post_date,
                    )
                )

            if posts:
                db.add_all(posts)
                db.flush()
                db.add_all(
                    QueryPost(query_id=query_id, post_id=post.post_id) for post in posts
                )
                _persist_predictions(db, posts, model_id, get_predictor(model_id))

            query.post_count = len(posts)
            query.status = QueryStatus.done
            query.finished_at = datetime.now(UTC)
            db.commit()

            logger.info(
                "CSV query %s completed: %s posts, %s invalid-date rows skipped",
                query_id,
                len(posts),
                skipped_rows + skipped_invalid_dates,
            )
    except Exception as exc:
        logger.exception("CSV query %s failed", query_id)
        _mark_query_failed(
            query_id,
            str(exc) or "CSV processing failed",
            session_factory,
            "CSV",
        )


def _validate_reddit_post(post: RedditPost) -> RedditPostValues:
    external_id = post.get("external_id")
    text = post.get("text")
    if not isinstance(external_id, str) or not external_id.strip():
        raise ValueError("Reddit post is missing a valid external_id")
    external_id = external_id.strip()
    if len(external_id) > 50:
        raise ValueError("Reddit post external_id exceeds 50 characters")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Reddit post is missing valid text")

    post_date = post.get("post_date")
    if post_date is not None and not isinstance(post_date, datetime):
        raise ValueError("Reddit post post_date must be a datetime or None")
    if post_date is not None and post_date.tzinfo is None:
        post_date = post_date.replace(tzinfo=UTC)

    score = post.get("score")
    if score is not None and not isinstance(score, int):
        raise ValueError("Reddit post score must be an integer or None")

    author = post.get("author")
    subreddit = post.get("subreddit")
    url = post.get("url")
    for field_name, field_value in (
        ("author", author),
        ("subreddit", subreddit),
        ("url", url),
    ):
        if field_value is not None and not isinstance(field_value, str):
            raise ValueError(f"Reddit post {field_name} must be a string or None")

    return {
        "external_id": external_id,
        "source": PostSource.reddit,
        "text": text,
        "clean_text": clean_text(text),
        "author": author,
        "subreddit": subreddit,
        "url": url,
        "score": score,
        "post_date": post_date,
    }


def run_keyword_job(
    query_id: int,
    *,
    fetch_posts: FetchPosts | None = None,
    session_factory: SessionFactory = SessionLocal,
) -> None:
    try:
        with session_factory() as db:
            query = db.get(SearchQuery, query_id)
            if query is None:
                raise LookupError(f"Keyword query {query_id} was not found")
            if query.type != QueryType.keyword:
                raise ValueError(f"Query {query_id} is not a keyword query")
            if query.status != QueryStatus.pending:
                raise ValueError(f"Keyword query {query_id} is not pending")
            if query.model_id is None:
                raise LookupError(f"Keyword query {query_id} has no model configured")
            if not query.keyword:
                raise ValueError(f"Keyword query {query_id} has no keyword")

            params = query.params or {}
            limit = params.get("limit")
            time_range = params.get("time_range")
            if not isinstance(limit, int) or not 10 <= limit <= 500:
                raise ValueError(f"Keyword query {query_id} has an invalid limit")
            if time_range not in ALLOWED_TIME_RANGES:
                raise ValueError(f"Keyword query {query_id} has an invalid time range")

            model_id = query.model_id
            keyword = query.keyword
            query.status = QueryStatus.processing
            query.error_message = None
            db.commit()

            if fetch_posts is None:
                from app.services.reddit import fetch_posts as dataset_fetch_posts

                fetch_posts = dataset_fetch_posts

            fetched_posts = fetch_posts(keyword, limit, time_range)
            post_values = [_validate_reddit_post(post) for post in fetched_posts]
            unique_values = {}
            for post in post_values:
                unique_values.setdefault(post["external_id"], post)

            posts: list[Post] = []
            if unique_values:
                db.execute(
                    insert(Post)
                    .values(list(unique_values.values()))
                    .on_conflict_do_nothing(constraint="uq_posts_source_external_id")
                )
                db.flush()

                posts = db.scalars(
                    select(Post).where(
                        Post.source == PostSource.reddit,
                        Post.external_id.in_(unique_values),
                    )
                ).all()
                posts_by_id = {post.post_id: post for post in posts}

                db.execute(
                    insert(QueryPost)
                    .values(
                        [
                            {"query_id": query_id, "post_id": post_id}
                            for post_id in posts_by_id
                        ]
                    )
                    .on_conflict_do_nothing(index_elements=["query_id", "post_id"])
                )

                existing_predictions = set(
                    db.scalars(
                        select(Prediction.post_id).where(
                            Prediction.model_id == model_id,
                            Prediction.post_id.in_(posts_by_id),
                        )
                    ).all()
                )
                posts_to_predict = [
                    post for post in posts if post.post_id not in existing_predictions
                ]

                for post in posts_to_predict:
                    if not post.clean_text:
                        post.clean_text = clean_text(post.text)

                if posts_to_predict:
                    _persist_predictions(
                        db,
                        posts_to_predict,
                        model_id,
                        get_predictor(model_id),
                    )

            query.post_count = len(posts)
            query.status = QueryStatus.done
            query.finished_at = datetime.now(UTC)
            db.commit()

            logger.info(
                "Keyword query %s completed: %s unique Reddit posts",
                query_id,
                len(posts),
            )
    except Exception as exc:
        logger.exception("Keyword query %s failed", query_id)
        _mark_query_failed(
            query_id,
            str(exc) or "Keyword processing failed",
            session_factory,
            "keyword",
        )
