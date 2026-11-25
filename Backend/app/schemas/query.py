from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.query import QueryStatus, QueryType
from app.schemas.analyze import PredictionResponse


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
    positive_share: float | None = None
    created_at: datetime
    finished_at: datetime | None


class QueryListResponse(BaseModel):
    items: list[QueryResponse]
    total: int


class QueryAcceptedResponse(BaseModel):
    query_id: int
    status: QueryStatus


class KeywordQueryRequest(BaseModel):
    keyword: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ]
    limit: Annotated[int, Field(ge=10, le=500)] = 100
    time_range: Literal["day", "week", "month", "year", "all"] = "week"


class PostWithPredictionResponse(BaseModel):
    post_id: int
    text: str
    author: str | None
    subreddit: str | None
    url: str | None
    post_date: datetime | None
    prediction: PredictionResponse


class PostListResponse(BaseModel):
    items: list[PostWithPredictionResponse]
    total: int
