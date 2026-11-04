import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PostSource(str, enum.Enum):
    reddit = "reddit"
    csv = "csv"
    manual = "manual"


class Post(Base):
    __tablename__ = "posts"

    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            name="uq_posts_source_external_id",
        ),
    )

    post_id: Mapped[int] = mapped_column(primary_key=True)

    external_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    source: Mapped[PostSource] = mapped_column(
        Enum(PostSource, name="post_source"),
    )

    text: Mapped[str] = mapped_column(Text)

    clean_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    author: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    subreddit: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    post_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )