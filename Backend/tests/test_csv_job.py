from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy import select

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


def create_csv_query(db):
    user = User(
        username="csvuser",
        email="csvuser@example.com",
        password_hash="fake-hash",
        role=UserRole.user,
    )
    model = Model(name="baseline", version="1.0", is_active=True)
    db.add_all([user, model])
    db.flush()

    query = SearchQuery(
        user_id=user.user_id,
        type=QueryType.csv,
        file_name="reviews.csv",
        model_id=model.model_id,
        status=QueryStatus.pending,
    )
    db.add(query)
    db.flush()
    return query


def make_session_factory(db_connection):
    def session_factory():
        from sqlalchemy.orm import Session

        return Session(
            bind=db_connection,
            autoflush=False,
            join_transaction_mode="create_savepoint",
        )

    return session_factory


def test_run_csv_job_persists_posts_links_and_predictions(
    db, db_connection, monkeypatch
):
    query = create_csv_query(db)
    query_id = query.query_id
    predictor = FakePredictor()
    monkeypatch.setattr(jobs, "clean_text", lambda text: text.lower())
    monkeypatch.setattr(jobs, "get_predictor", lambda model_id: predictor)

    jobs.run_csv_job(
        query_id,
        [
            {"text": "Great product", "date": "2026-11-10"},
            {"text": "Invalid date row", "date": "not-a-date"},
            {"text": "Works well", "date": None},
        ],
        session_factory=make_session_factory(db_connection),
    )

    db.expire_all()
    saved_query = db.get(SearchQuery, query_id)
    posts = db.scalars(select(Post).order_by(Post.post_id)).all()
    links = db.scalars(select(QueryPost).where(QueryPost.query_id == query_id)).all()
    predictions = db.scalars(select(Prediction)).all()

    assert saved_query.status == QueryStatus.done
    assert saved_query.post_count == 2
    assert saved_query.finished_at is not None
    assert saved_query.error_message is None
    assert [post.text for post in posts] == ["Great product", "Works well"]
    assert all(post.source == PostSource.csv for post in posts)
    assert [post.clean_text for post in posts] == ["great product", "works well"]
    assert posts[0].post_date == datetime(2026, 11, 10, tzinfo=UTC)
    assert posts[1].post_date is None
    assert len(links) == len(predictions) == 2
    assert all(item.sentiment == SentimentLabel.positive for item in predictions)
    assert predictor.batches == [["great product", "works well"]]


def test_run_csv_job_completes_when_every_row_has_invalid_date(
    db, db_connection, monkeypatch
):
    query = create_csv_query(db)
    query_id = query.query_id
    monkeypatch.setattr(jobs, "clean_text", lambda text: text)
    monkeypatch.setattr(
        jobs,
        "get_predictor",
        lambda _: (_ for _ in ()).throw(AssertionError("predictor should not load")),
    )

    jobs.run_csv_job(
        query_id,
        [{"text": "Kept only if date parses", "date": "invalid"}],
        session_factory=make_session_factory(db_connection),
    )

    db.expire_all()
    saved_query = db.get(SearchQuery, query_id)
    assert saved_query.status == QueryStatus.done
    assert saved_query.post_count == 0
    assert db.scalars(select(Post)).all() == []


def test_run_csv_job_predicts_in_batches_of_32(db, db_connection, monkeypatch):
    query = create_csv_query(db)
    query_id = query.query_id
    predictor = FakePredictor()
    monkeypatch.setattr(jobs, "clean_text", lambda text: text)
    monkeypatch.setattr(jobs, "get_predictor", lambda _: predictor)

    jobs.run_csv_job(
        query_id,
        [{"text": f"Post {index}", "date": None} for index in range(33)],
        session_factory=make_session_factory(db_connection),
    )

    db.expire_all()
    saved_query = db.get(SearchQuery, query_id)
    assert saved_query.status == QueryStatus.done
    assert saved_query.post_count == 33
    assert [len(batch) for batch in predictor.batches] == [32, 1]


def test_run_csv_job_marks_query_failed_and_rolls_back_partial_data(
    db, db_connection, monkeypatch
):
    query = create_csv_query(db)
    query_id = query.query_id
    monkeypatch.setattr(jobs, "clean_text", lambda text: text)

    def fail_prediction(_model_id):
        raise RuntimeError("predictor unavailable")

    monkeypatch.setattr(jobs, "get_predictor", fail_prediction)

    jobs.run_csv_job(
        query_id,
        [{"text": "A valid row", "date": None}],
        session_factory=make_session_factory(db_connection),
    )

    db.expire_all()
    saved_query = db.get(SearchQuery, query_id)
    assert saved_query.status == QueryStatus.failed
    assert saved_query.error_message == "predictor unavailable"
    assert saved_query.finished_at is not None
    assert db.scalars(select(Post)).all() == []
    assert db.scalars(select(QueryPost)).all() == []
    assert db.scalars(select(Prediction)).all() == []
