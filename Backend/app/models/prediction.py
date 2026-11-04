import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SentimentLabel(str, enum.Enum):
    negative = "negative"
    neutral = "neutral"
    positive = "positive"


class Prediction(Base):
    __tablename__ = "predictions"

    __table_args__ = (
        UniqueConstraint(
            "post_id",
            "model_id",
            name="uq_predictions_post_model",
        ),
    )

    prediction_id: Mapped[int] = mapped_column(primary_key=True)

    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.post_id")
    )

    model_id: Mapped[int] = mapped_column(
        ForeignKey("models.model_id")
    )

    sentiment: Mapped[SentimentLabel] = mapped_column(
        Enum(SentimentLabel, name="sentiment_label")
    )

    confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4)
    )

    prob_positive: Mapped[Decimal] = mapped_column(
        Numeric(5, 4)
    )

    prob_neutral: Mapped[Decimal] = mapped_column(
        Numeric(5, 4)
    )

    prob_negative: Mapped[Decimal] = mapped_column(
        Numeric(5, 4)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )