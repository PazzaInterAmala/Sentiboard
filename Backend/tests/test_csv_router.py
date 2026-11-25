from fastapi.testclient import TestClient
from sqlalchemy import select

from app.ml.registry import register_predictor
from app.models.model import Model
from app.models.query import QueryStatus, QueryType, SearchQuery
from app.models.user import User, UserRole
from app.services.auth import create_access_token


class FakePredictor:
    def predict(self, texts: list[str]):
        return []


def create_authenticated_user(db):
    user = User(
        username="csvrouter",
        email="csvrouter@example.com",
        password_hash="test-hash",
        role=UserRole.user,
    )
    db.add(user)
    db.flush()
    return user, create_access_token(user)


def create_active_model(db):
    model = Model(name="baseline", version="1.0", is_active=True)
    db.add(model)
    db.flush()
    return model


def test_create_csv_query_returns_202_and_schedules_job(
    client: TestClient, db, monkeypatch
):
    user, token = create_authenticated_user(db)
    model = create_active_model(db)
    register_predictor(model.model_id, FakePredictor())
    scheduled = []
    monkeypatch.setattr(
        "app.routers.queries.run_csv_job",
        lambda *args, **kwargs: scheduled.append((args, kwargs)),
    )

    response = client.post(
        "/queries/csv",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": (
                "reviews.csv",
                b"text,date\nGreat product,2026-11-10\n",
                "text/csv",
            )
        },
        data={"text_column": "text", "date_column": "date"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "pending"

    query = db.get(SearchQuery, payload["query_id"])
    assert query is not None
    assert query.user_id == user.user_id
    assert query.type == QueryType.csv
    assert query.file_name == "reviews.csv"
    assert query.model_id == model.model_id
    assert query.status == QueryStatus.pending
    assert query.params == {
        "text_column": "text",
        "date_column": "date",
        "skipped_rows": 0,
    }

    assert len(scheduled) == 1
    args, kwargs = scheduled[0]
    assert args[0] == query.query_id
    assert args[1] == [{"text": "Great product", "date": "2026-11-10"}]
    assert kwargs == {"skipped_rows": 0}


def test_create_csv_query_rejects_invalid_file_without_creating_query(
    client: TestClient, db, monkeypatch
):
    _, token = create_authenticated_user(db)
    model = create_active_model(db)
    register_predictor(model.model_id, FakePredictor())
    monkeypatch.setattr(
        "app.routers.queries.run_csv_job",
        lambda *_args, **_kwargs: None,
    )

    response = client.post(
        "/queries/csv",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("reviews.csv", b"review\nGreat\n", "text/csv")},
        data={"text_column": "text"},
    )

    assert response.status_code == 400
    assert "Text column" in response.json()["detail"]
    assert (
        db.scalars(select(SearchQuery).where(SearchQuery.type == QueryType.csv)).all()
        == []
    )


def test_create_csv_query_requires_authentication(client: TestClient):
    response = client.post(
        "/queries/csv",
        files={"file": ("reviews.csv", b"text\nGreat\n", "text/csv")},
        data={"text_column": "text"},
    )

    assert response.status_code == 401


def test_create_csv_query_rejects_upload_over_size_limit(client: TestClient, db):
    _, token = create_authenticated_user(db)
    model = create_active_model(db)
    register_predictor(model.model_id, FakePredictor())

    response = client.post(
        "/queries/csv",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("large.csv", b"x" * (5 * 1024 * 1024 + 1), "text/csv")},
        data={"text_column": "text"},
    )

    assert response.status_code == 400
    assert "5 MB limit" in response.json()["detail"]
    assert (
        db.scalars(select(SearchQuery).where(SearchQuery.type == QueryType.csv)).all()
        == []
    )
