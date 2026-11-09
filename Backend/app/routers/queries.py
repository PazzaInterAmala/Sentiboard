from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Float, case, cast, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.prediction import Prediction, SentimentLabel
from app.models.query import QueryPost, QueryStatus, SearchQuery
from app.models.user import User
from app.schemas.query import QueryListResponse, QueryResponse
from app.services.auth import get_current_user

router = APIRouter(
    prefix="/queries",
    tags=["queries"],
)


def _positive_share_expression():
    positive_count = func.sum(
        case(
            (Prediction.sentiment == SentimentLabel.positive, 1),
            else_=0,
        )
    )
    prediction_count = func.count(Prediction.prediction_id)

    share = (
        select(cast(positive_count, Float) / func.nullif(prediction_count, 0))
        .select_from(QueryPost)
        .join(Prediction, Prediction.post_id == QueryPost.post_id)
        .where(
            QueryPost.query_id == SearchQuery.query_id,
            Prediction.model_id == SearchQuery.model_id,
        )
        .correlate(SearchQuery)
        .scalar_subquery()
    )

    return case(
        (SearchQuery.status == QueryStatus.done, share),
        else_=None,
    )


@router.get("", response_model=QueryListResponse)
def list_queries(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> QueryListResponse:
    total = db.scalar(
        select(func.count())
        .select_from(SearchQuery)
        .where(SearchQuery.user_id == current_user.user_id)
    )

    rows = db.execute(
        select(SearchQuery, _positive_share_expression())
        .where(SearchQuery.user_id == current_user.user_id)
        .order_by(SearchQuery.created_at.desc(), SearchQuery.query_id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return QueryListResponse(
        items=[
            QueryResponse.model_validate(query).model_copy(
                update={"positive_share": positive_share}
            )
            for query, positive_share in rows
        ],
        total=total or 0,
    )


@router.get("/{query_id}", response_model=QueryResponse)
def get_query(
    query_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QueryResponse:
    row = db.execute(
        select(SearchQuery, _positive_share_expression()).where(
            SearchQuery.query_id == query_id,
            SearchQuery.user_id == current_user.user_id,
        )
    ).one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="Query not found")

    query, positive_share = row
    return QueryResponse.model_validate(query).model_copy(
        update={"positive_share": positive_share}
    )
