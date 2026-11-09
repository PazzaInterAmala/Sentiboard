from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.query import QueryStatus, QueryType


class QueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query_id: int
    type: QueryType
    keyword: str | None
    file_name: str | None
    params: dict | None
    status: QueryStatus
    post_count: int | None
    error_message: str | None
    positive_share: float | None
    created_at: datetime
    finished_at: datetime | None


class QueryListResponse(BaseModel):
    items: list[QueryResponse]
    total: int
