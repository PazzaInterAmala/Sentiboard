from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.model import Model
from app.models.post import Post, PostSource
from app.models.prediction import Prediction, SentimentLabel
from app.models.query import QueryPost, QueryStatus, QueryType, SearchQuery
from app.models.user import User, UserRole
from app.services import jobs


class FakePredictor:
    def __init__(self):
        self.batches = []

    def predict(self, texts: list[str]):
        self.batches.append(texts)
        return [
            SimpleNamespace(
                label="positive",
                confidence=0.9,
                probabilities={
                    "positive": 0.9,
                    "neutral": 0.07,
                    "negative": 0.03,
                },
            )
            for _ in texts
        ]


def create_keyword_query(db):
    user = User(
        username="keyworduser",
        email="keyworduser@example.com",
        password_hash="fake-hash",
        role=UserRole.user,
    )
    model = Model(name="baseline", version="1.0", is_active=True)
    db.add_all([user, model])
    db.flush()

    query = SearchQuery(
        user_id=user.user_id,
        type=QueryType.keyword,
        keyword="camera",
        params={"limit": 25, "time_range": "month"},
        model_id=model.model_id,
        status=QueryStatus.pending,
    )
    db.add(query)
    db.flush()
    return query


def make_session_factory(db_connection):
    def session_factory():
        return Session(
            bind=db_connection,
            autoflush=False,
            join_transaction_mode="create_savepoint",
        )

    return session_factory


def test_run_keyword_job_fetches_deduplicates_and_predicts_missing_posts(
    db, db_connection, monkeypatch
):
    query = create_keyword_query(db)
    query_id = query.query_id
    model_id = query.model_id
    existing_post = Post(
        external_id="t3-existing",
        source=PostSource.reddit,
        text="Previously analyzed post",
        clean_text="previously analyzed post",
        post_date=datetime(2026, 11, 1, tzinfo=UTC),
    )
    existing_without_prediction = Post(
        external_id="t3-no-prediction",
        source=PostSource.reddit,
        text="Old post without a prediction",
    )
    db.add_all([existing_post, existing_without_prediction])
    db.flush()
    db.add(
        Prediction(
            post_id=existing_post.post_id,
            model_id=model_id,
            sentiment=SentimentLabel.neutral,
            confidence=0.8,
            prob_positive=0.1,
            prob_neutral=0.8,
            prob_negative=0.1,
        )
    )
    db.flush()

    predictor = FakePredictor()
    monkeypatch.setattr(jobs, "clean_text", lambda text: text.lower())
    monkeypatch.setattr(jobs, "get_predictor", lambda _: predictor)
    fetch_calls = []

    def fetch_posts(keyword: str, limit: int, time_range: str):
        fetch_calls.append((keyword, limit, time_range))
        return [
            {
                "external_id": "t3-existing",
                "text": "Updated duplicate",
                "post_date": datetime(2026, 11, 2, tzinfo=UTC),
            },
            {
                "external_id": "t3-no-prediction",
                "text": "Fetched old post",
            },
            {
                "external_id": "t3-new",
                "text": "New camera review",
                "author": "sample-user",
                "subreddit": "photography",
                "url": "https://example.test/post",
                "score": 12,
                "post_date": datetime(2026, 11, 3),
            },
            {
                "external_id": "t3-new",
                "text": "Duplicate fetched result",
            },
        ]

    jobs.run_keyword_job(
        query_id,
        fetch_posts=fetch_posts,
        session_factory=make_session_factory(db_connection),
    )

    db.expire_all()
    saved_query = db.get(SearchQuery, query_id)
    posts = db.scalars(select(Post).order_by(Post.external_id)).all()
    links = db.scalars(select(QueryPost).where(QueryPost.query_id == query_id)).all()
    predictions = db.scalars(select(Prediction).order_by(Prediction.post_id)).all()

    assert fetch_calls == [("camera", 25, "month")]
    assert saved_query.status == QueryStatus.done
    assert saved_query.post_count == 3
    assert saved_query.finished_at is not None
    assert saved_query.error_message is None
    assert len(posts) == len(links) == len(predictions) == 3

    new_post = next(post for post in posts if post.external_id == "t3-new")
    reused_post = next(post for post in posts if post.external_id == "t3-no-prediction")
    assert new_post.source == PostSource.reddit
    assert new_post.text == "New camera review"
    assert new_post.clean_text == "new camera review"
    assert new_post.author == "sample-user"
    assert new_post.subreddit == "photography"
    assert new_post.url == "https://example.test/post"
    assert new_post.score == 12
    assert new_post.post_date == datetime(2026, 11, 3, tzinfo=UTC)
    assert reused_post.text == "Old post without a prediction"
    assert reused_post.clean_text == "old post without a prediction"
    assert {text for batch in predictor.batches for text in batch} == {
        "new camera review",
        "old post without a prediction",
    }
    assert {prediction.post_id for prediction in predictions} == {
        existing_post.post_id,
        existing_without_prediction.post_id,
        new_post.post_id,
    }


def test_run_keyword_job_completes_when_no_posts_match(db, db_connection, monkeypatch):
    query = create_keyword_query(db)
    query_id = query.query_id
    monkeypatch.setattr(
        jobs,
        "get_predictor",
        lambda _: (_ for _ in ()).throw(AssertionError("predictor should not load")),
    )

    jobs.run_keyword_job(
        query_id,
        fetch_posts=lambda *_: [],
        session_factory=make_session_factory(db_connection),
    )

    db.expire_all()
    saved_query = db.get(SearchQuery, query_id)
    assert saved_query.status == QueryStatus.done
    assert saved_query.post_count == 0
    assert saved_query.finished_at is not None
    assert db.scalars(select(Post)).all() == []


def test_run_keyword_job_marks_query_failed_when_fetch_provider_raises(
    db, db_connection
):
    query = create_keyword_query(db)
    query_id = query.query_id

    def fetch_posts(*_):
        raise RuntimeError("Dataset is unavailable")

    jobs.run_keyword_job(
        query_id,
        fetch_posts=fetch_posts,
        session_factory=make_session_factory(db_connection),
    )

    db.expire_all()
    saved_query = db.get(SearchQuery, query_id)
    assert saved_query.status == QueryStatus.failed
    assert saved_query.error_message == "Dataset is unavailable"
    assert saved_query.finished_at is not None
    assert db.scalars(select(Post)).all() == []


def test_run_keyword_job_rolls_back_posts_when_prediction_fails(
    db, db_connection, monkeypatch
):
    query = create_keyword_query(db)
    query_id = query.query_id
    monkeypatch.setattr(jobs, "clean_text", lambda text: text)
    monkeypatch.setattr(
        jobs,
        "get_predictor",
        lambda _: (_ for _ in ()).throw(RuntimeError("Predictor unavailable")),
    )

    jobs.run_keyword_job(
        query_id,
        fetch_posts=lambda *_: [{"external_id": "t3-new", "text": "A post"}],
        session_factory=make_session_factory(db_connection),
    )

    db.expire_all()
    saved_query = db.get(SearchQuery, query_id)
    assert saved_query.status == QueryStatus.failed
    assert saved_query.error_message == "Predictor unavailable"
    assert db.scalars(select(Post)).all() == []
    assert db.scalars(select(QueryPost)).all() == []
    assert db.scalars(select(Prediction)).all() == []


def test_run_keyword_job_fails_for_invalid_post_data(db, db_connection, monkeypatch):
    query = create_keyword_query(db)
    query_id = query.query_id
    monkeypatch.setattr(jobs, "clean_text", lambda text: text)

    jobs.run_keyword_job(
        query_id,
        fetch_posts=lambda *_: [{"text": "Missing Reddit ID"}],
        session_factory=make_session_factory(db_connection),
    )

    db.expire_all()
    saved_query = db.get(SearchQuery, query_id)
    assert saved_query.status == QueryStatus.failed
    assert saved_query.error_message == "Reddit post is missing a valid external_id"
    assert db.scalars(select(Post)).all() == []
