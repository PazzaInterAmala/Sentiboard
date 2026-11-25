from datetime import UTC, datetime
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.model import Model
from app.models.post import Post, PostSource
from app.models.prediction import Prediction, SentimentLabel
from app.models.query import QueryPost, QueryStatus, QueryType, SearchQuery


class PredictionData(TypedDict):
    model_id: int
    label: SentimentLabel
    confidence: float
    prob_positive: float
    prob_neutral: float
    prob_negative: float


def persist_text_analysis(
    db: Session,
    *,
    user_id: int,
    text: str,
    cleaned_text: str,
    predictions: list[PredictionData],
    primary_model_id: int,
) -> SearchQuery:
    if not predictions:
        raise ValueError("At least one prediction is required")

    if not any(p["model_id"] == primary_model_id for p in predictions):
        raise ValueError("Primary model must be included in predictions")

    try:
        query = SearchQuery(
            user_id=user_id,
            type=QueryType.text,
            keyword=text[:100],
            model_id=primary_model_id,
            status=QueryStatus.done,
            post_count=1,
            finished_at=datetime.now(UTC),
        )

        post = Post(
            source=PostSource.manual,
            text=text,
            clean_text=cleaned_text,
        )

        db.add_all([query, post])
        db.flush()

        db.add(
            QueryPost(
                query_id=query.query_id,
                post_id=post.post_id,
            )
        )

        for result in predictions:
            db.add(
                Prediction(
                    post_id=post.post_id,
                    model_id=result["model_id"],
                    sentiment=result["label"],
                    confidence=result["confidence"],
                    prob_positive=result["prob_positive"],
                    prob_neutral=result["prob_neutral"],
                    prob_negative=result["prob_negative"],
                )
            )

        db.commit()
        db.refresh(query)

        return query

    except Exception:
        db.rollback()
        raise


def get_active_model(db: Session) -> Model:
    model = db.scalar(select(Model).where(Model.is_active.is_(True)))

    if model is None:
        raise LookupError("No active model is configured")

    return model


def get_comparison_model(
    db: Session,
    active_model_id: int,
    available_model_ids: set[int],
) -> Model | None:
    return db.scalar(
        select(Model)
        .where(
            Model.model_id.in_(available_model_ids),
            Model.model_id != active_model_id,
        )
        .order_by(
            Model.trained_at.desc().nullslast(),
            Model.model_id.desc(),
        )
    )
