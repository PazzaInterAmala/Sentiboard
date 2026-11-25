import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class QueryType(str, enum.Enum):
    text = "text"
    keyword = "keyword"
    csv = "csv"


class QueryStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"


class SearchQuery(Base):
    __tablename__ = "search_queries"

    query_id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))

    type: Mapped[QueryType] = mapped_column(Enum(QueryType, name="query_type"))

    keyword: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    file_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    params: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    model_id: Mapped[int | None] = mapped_column(
        ForeignKey("models.model_id"),
        nullable=True,
    )

    status: Mapped[QueryStatus] = mapped_column(
        Enum(QueryStatus, name="query_status"),
        default=QueryStatus.pending,
        server_default="pending",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    post_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class QueryPost(Base):
    __tablename__ = "query_posts"

    __table_args__ = (Index("ix_query_posts_post_id", "post_id"),)

    query_id: Mapped[int] = mapped_column(
        ForeignKey("search_queries.query_id", ondelete="CASCADE"),
        primary_key=True,
    )

    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.post_id", ondelete="CASCADE"),
        primary_key=True,
    )


Index(
    "ix_search_queries_user_created_at",
    SearchQuery.user_id,
    SearchQuery.created_at.desc(),
)
