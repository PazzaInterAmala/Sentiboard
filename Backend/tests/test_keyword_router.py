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
        username="keywordrouter",
        email="keywordrouter@example.com",
        password_hash="test-hash",
        role=UserRole.user,
    )
    db.add(user)
    db.flush()
    return user, create_access_token(user)


def test_create_keyword_query_returns_202_and_schedules_job(
    client: TestClient, db, monkeypatch
):
    user, token = create_authenticated_user(db)
    model = Model(name="baseline", version="1.0", is_active=True)
    db.add(model)
    db.flush()
    register_predictor(model.model_id, FakePredictor())
    scheduled = []
    monkeypatch.setattr(
        "app.routers.queries.run_keyword_job",
        lambda *args, **kwargs: scheduled.append((args, kwargs)),
    )

    response = client.post(
        "/queries/keyword",
        headers={"Authorization": f"Bearer {token}"},
        json={"keyword": "  camera  ", "limit": 25, "time_range": "month"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "pending"

    query = db.get(SearchQuery, payload["query_id"])
    assert query is not None
    assert query.user_id == user.user_id
    assert query.type == QueryType.keyword
    assert query.keyword == "camera"
    assert query.params == {"limit": 25, "time_range": "month"}
    assert query.model_id == model.model_id
    assert query.status == QueryStatus.pending
    assert scheduled == [((query.query_id,), {})]


def test_create_keyword_query_uses_defaults(client: TestClient, db, monkeypatch):
    _, token = create_authenticated_user(db)
    model = Model(name="baseline", version="1.0", is_active=True)
    db.add(model)
    db.flush()
    register_predictor(model.model_id, FakePredictor())
    monkeypatch.setattr(
        "app.routers.queries.run_keyword_job",
        lambda *_args, **_kwargs: None,
    )

    response = client.post(
        "/queries/keyword",
        headers={"Authorization": f"Bearer {token}"},
        json={"keyword": "camera"},
    )

    assert response.status_code == 202
    query = db.get(SearchQuery, response.json()["query_id"])
    assert query.params == {"limit": 100, "time_range": "week"}


def test_create_keyword_query_rejects_invalid_input_without_creating_query(
    client: TestClient, db
):
    _, token = create_authenticated_user(db)

    response = client.post(
        "/queries/keyword",
        headers={"Authorization": f"Bearer {token}"},
        json={"keyword": "   ", "limit": 5, "time_range": "decade"},
    )

    assert response.status_code == 422
    assert (
        db.scalars(
            select(SearchQuery).where(SearchQuery.type == QueryType.keyword)
        ).all()
        == []
    )


def test_create_keyword_query_requires_authentication(client: TestClient):
    response = client.post(
        "/queries/keyword",
        json={"keyword": "camera"},
    )

    assert response.status_code == 401


def test_create_keyword_query_requires_active_model(client: TestClient, db):
    _, token = create_authenticated_user(db)

    response = client.post(
        "/queries/keyword",
        headers={"Authorization": f"Bearer {token}"},
        json={"keyword": "camera"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "No active model is configured"


def test_create_keyword_query_requires_registered_predictor(client: TestClient, db):
    _, token = create_authenticated_user(db)
    db.add(Model(name="baseline", version="1.0", is_active=True))
    db.flush()

    response = client.post(
        "/queries/keyword",
        headers={"Authorization": f"Bearer {token}"},
        json={"keyword": "camera"},
    )

    assert response.status_code == 503
    assert "No predictor registered" in response.json()["detail"]
