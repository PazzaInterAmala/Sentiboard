import pytest
from sqlalchemy import select

from app.models.model import Model
from app.models.post import Post, PostSource
from app.models.prediction import Prediction, SentimentLabel
from app.models.query import QueryPost, QueryStatus, QueryType
from app.models.user import User, UserRole
from app.services.analyze import (
    get_active_model,
    persist_text_analysis,
)


def test_persist_text_analysis(db):
    user = User(
        username="testuser",
        email="testuser@example.com",
        password_hash="fake-hash",
        role=UserRole.user,
    )
    db.add(user)
    db.flush()
    # Create a test model
    model = Model(
        name="test-model",
        version="1.0",
    )
    db.add(model)
    db.flush()

    # Execute the service
    query = persist_text_analysis(
        db,
        user_id=user.user_id,
        text="This product is amazing!",
        cleaned_text="product amazing",
        predictions=[
            {
                "model_id": model.model_id,
                "label": SentimentLabel.positive,
                "confidence": 0.95,
                "prob_positive": 0.95,
                "prob_neutral": 0.03,
                "prob_negative": 0.02,
            }
        ],
        primary_model_id=model.model_id,
    )

    # Verify the search query
    assert query.query_id is not None
    assert query.type == QueryType.text
    assert query.status == QueryStatus.done
    assert query.post_count == 1
    assert query.finished_at is not None

    # Verify the post
    post = db.scalar(select(Post).where(Post.text == "This product is amazing!"))
    assert post is not None
    assert post.source == PostSource.manual
    assert post.clean_text == "product amazing"

    # Verify the query-post relationship
    link = db.scalar(
        select(QueryPost).where(
            QueryPost.query_id == query.query_id,
            QueryPost.post_id == post.post_id,
        )
    )
    assert link is not None

    # Verify the prediction
    prediction = db.scalar(
        select(Prediction).where(
            Prediction.post_id == post.post_id,
            Prediction.model_id == model.model_id,
        )
    )
    assert prediction is not None
    assert prediction.sentiment == SentimentLabel.positive
    assert float(prediction.confidence) == 0.95


def test_persist_text_analysis_with_two_models(db):
    # Create a test user
    user = User(
        username="compareuser",
        email="compareuser@example.com",
        password_hash="fake-hash",
        role=UserRole.user,
    )
    db.add(user)
    db.flush()

    # Create two test models
    model_a = Model(name="test-model-a", version="1.0")
    model_b = Model(name="test-model-b", version="1.0")

    db.add_all([model_a, model_b])
    db.flush()

    # Execute the service with two predictions
    query = persist_text_analysis(
        db,
        user_id=user.user_id,
        text="This product is amazing!",
        cleaned_text="product amazing",
        predictions=[
            {
                "model_id": model_a.model_id,
                "label": SentimentLabel.positive,
                "confidence": 0.95,
                "prob_positive": 0.95,
                "prob_neutral": 0.03,
                "prob_negative": 0.02,
            },
            {
                "model_id": model_b.model_id,
                "label": SentimentLabel.neutral,
                "confidence": 0.70,
                "prob_positive": 0.20,
                "prob_neutral": 0.70,
                "prob_negative": 0.10,
            },
        ],
        primary_model_id=model_a.model_id,
    )

    # Verify the primary model
    assert query.model_id == model_a.model_id
    assert query.status == QueryStatus.done

    # Retrieve the associated post
    link = db.scalar(select(QueryPost).where(QueryPost.query_id == query.query_id))
    assert link is not None

    # Verify both predictions
    predictions = db.scalars(
        select(Prediction).where(Prediction.post_id == link.post_id)
    ).all()

    assert len(predictions) == 2

    model_ids = {prediction.model_id for prediction in predictions}
    assert model_ids == {model_a.model_id, model_b.model_id}


def test_get_active_model(db):
    model = Model(
        name="active-model",
        version="1.0",
        is_active=True,
    )
    db.add(model)
    db.flush()

    active_model = get_active_model(db)

    assert active_model is not None
    assert active_model.model_id == model.model_id
    assert active_model.name == "active-model"


def test_get_active_model_when_none_exists(db):
    with pytest.raises(
        LookupError,
        match="No active model is configured",
    ):
        get_active_model(db)
