from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Model(Base):
    __tablename__ = "models"

    __table_args__ = (
        UniqueConstraint(
            "name",
            "version",
            name="uq_models_name_version",
        ),
    )

    model_id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(50))

    version: Mapped[str] = mapped_column(String(20))

    accuracy: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )

    f1_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )

    trained_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )


Index(
    "uq_models_one_active",
    Model.is_active,
    unique=True,
    postgresql_where=Model.is_active.is_(True),
)
