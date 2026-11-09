from typing import ClassVar

from sqlalchemy import select

from app.ml import registry
from app.models.model import Model
from app.models.prediction import Prediction, SentimentLabel
from app.models.query import QueryPost
from app.models.user import User, UserRole
from app.services.auth import create_access_token


class FakePrediction:
    label = SentimentLabel.positive
    confidence = 0.95
    probabilities: ClassVar[dict[str, float]] = {
        "negative": 0.02,
        "neutral": 0.03,
        "positive": 0.95,
    }


class FakePredictor:
    name = "fake-model"
    version = "1.0"

    def predict(self, texts: list[str]) -> list[FakePrediction]:
        return [FakePrediction() for _ in texts]


class FakeComparisonPrediction:
    label = SentimentLabel.negative
    confidence = 0.80
    probabilities: ClassVar[dict[str, float]] = {
        "negative": 0.80,
        "neutral": 0.15,
        "positive": 0.05,
    }


class FakeComparisonPredictor:
    name = "comparison-model"
    version = "1.0"

    def predict(self, texts: list[str]) -> list[FakeComparisonPrediction]:
        return [FakeComparisonPrediction() for _ in texts]


def test_analyze_text_success(client, db, monkeypatch):
    # Create a test user
    user = User(
        username="analyzeuser",
        email="analyzeuser@example.com",
        password_hash="fake-hash",
        role=UserRole.user,
    )
    db.add(user)
    db.flush()

    # Create an active model
    model = Model(
        name="fake-model",
        version="1.0",
        is_active=True,
    )
    db.add(model)
    db.flush()

    # Register the fake predictor and preprocessor
    monkeypatch.setitem(
        registry.predictors,
        model.model_id,
        FakePredictor(),
    )
    monkeypatch.setattr(
        registry,
        "preprocessor",
        lambda text: text.strip().lower(),
    )

    # Generate authentication token
    token = create_access_token(user)

    # Send request
    response = client.post(
        "/analyze",
        json={
            "text": "This product is amazing!",
            "compare": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Verify HTTP response
    assert response.status_code == 200

    data = response.json()

    assert data["query_id"] is not None
    assert len(data["results"]) == 1

    result = data["results"][0]

    assert result["model"] == "fake-model"
    assert result["label"] == "positive"
    assert result["confidence"] == 0.95
    assert result["probabilities"]["positive"] == 0.95


def test_analyze_without_token(client):
    response = client.post(
        "/analyze",
        json={
            "text": "This product is amazing!",
            "compare": False,
        },
    )

    assert response.status_code == 401


def test_analyze_without_active_model(client, db):
    # Create a test user
    user = User(
        username="nomodeluser",
        email="nomodeluser@example.com",
        password_hash="fake-hash",
        role=UserRole.user,
    )
    db.add(user)
    db.flush()

    token = create_access_token(user)

    response = client.post(
        "/analyze",
        json={
            "text": "This product is amazing!",
            "compare": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "No active model is configured"


def test_analyze_without_registered_predictor(client, db):
    user = User(
        username="nopredictor",
        email="nopredictor@example.com",
        password_hash="fake-hash",
        role=UserRole.user,
    )
    db.add(user)
    db.flush()

    model = Model(
        name="missing-predictor",
        version="1.0",
        is_active=True,
    )
    db.add(model)
    db.flush()

    token = create_access_token(user)

    response = client.post(
        "/analyze",
        json={
            "text": "This product is amazing!",
            "compare": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        f"No predictor registered for model_id={model.model_id}"
    )


def test_analyze_with_invalid_text(client, db):
    user = User(
        username="invalidtextuser",
        email="invalidtextuser@example.com",
        password_hash="fake-hash",
        role=UserRole.user,
    )
    db.add(user)
    db.flush()

    token = create_access_token(user)

    invalid_texts = [
        "",
        "     ",
        "a" * 5001,
    ]

    for text in invalid_texts:
        response = client.post(
            "/analyze",
            json={
                "text": text,
                "compare": False,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422


def test_analyze_text_with_comparison(client, db, monkeypatch):
    user = User(
        username="compareuser",
        email="compareuser@example.com",
        password_hash="fake-hash",
        role=UserRole.user,
    )

    active_model = Model(
        name="fake-model",
        version="1.0",
        is_active=True,
    )

    comparison_model = Model(
        name="comparison-model",
        version="1.0",
        is_active=False,
    )

    db.add_all([user, active_model, comparison_model])
    db.flush()

    monkeypatch.setitem(
        registry.predictors,
        active_model.model_id,
        FakePredictor(),
    )

    monkeypatch.setitem(
        registry.predictors,
        comparison_model.model_id,
        FakeComparisonPredictor(),
    )

    monkeypatch.setattr(
        registry,
        "preprocessor",
        lambda text: text.strip().lower(),
    )

    token = create_access_token(user)

    response = client.post(
        "/analyze",
        json={
            "text": "This product is amazing!",
            "compare": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["results"]) == 2

    assert data["results"][0]["model"] == "fake-model"
    assert data["results"][0]["label"] == "positive"

    assert data["results"][1]["model"] == "comparison-model"
    assert data["results"][1]["label"] == "negative"

    query_post = db.scalar(
        select(QueryPost).where(QueryPost.query_id == data["query_id"])
    )

    assert query_post is not None

    saved_predictions = db.scalars(
        select(Prediction).where(Prediction.post_id == query_post.post_id)
    ).all()

    assert len(saved_predictions) == 2

    saved_model_ids = {p.model_id for p in saved_predictions}

    assert saved_model_ids == {
        active_model.model_id,
        comparison_model.model_id,
    }


def test_analyze_comparison_without_second_model(client, db, monkeypatch):
    user = User(
        username="singlemodeluser",
        email="singlemodeluser@example.com",
        password_hash="fake-hash",
        role=UserRole.user,
    )

    model = Model(
        name="single-model",
        version="1.0",
        is_active=True,
    )

    db.add_all([user, model])
    db.flush()

    monkeypatch.setitem(
        registry.predictors,
        model.model_id,
        FakePredictor(),
    )

    monkeypatch.setattr(
        registry,
        "preprocessor",
        lambda text: text.strip().lower(),
    )

    token = create_access_token(user)

    response = client.post(
        "/analyze",
        json={
            "text": "This product is amazing!",
            "compare": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "No second registered model is available for comparison"
    )