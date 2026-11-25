import csv
import io
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import Float, and_, case, cast, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.ml.registry import get_predictor
from app.models.model import Model
from app.models.post import Post
from app.models.prediction import Prediction, SentimentLabel
from app.models.query import QueryPost, QueryStatus, QueryType, SearchQuery
from app.models.user import User
from app.schemas.query import (
    KeywordQueryRequest,
    PostListResponse,
    PostWithPredictionResponse,
    QueryAcceptedResponse,
    QueryListResponse,
    QueryResponse,
)
from app.services.analyze import get_active_model
from app.services.auth import get_current_user
from app.services.csv_import import MAX_CSV_BYTES, parse_csv_upload
from app.services.jobs import run_csv_job, run_keyword_job

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


@router.post(
    "/csv",
    response_model=QueryAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_csv_query(
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: Annotated[UploadFile, File()],
    text_column: Annotated[str, Form()],
    date_column: Annotated[str | None, Form()] = None,
) -> QueryAcceptedResponse:
    content = file.file.read(MAX_CSV_BYTES + 1)

    try:
        rows, skipped_rows = parse_csv_upload(
            content=content,
            filename=file.filename or "",
            text_column=text_column,
            date_column=date_column or None,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        model = get_active_model(db)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    try:
        get_predictor(model.model_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    query = SearchQuery(
        user_id=current_user.user_id,
        type=QueryType.csv,
        file_name=file.filename,
        params={
            "text_column": text_column,
            "date_column": date_column or None,
            "skipped_rows": skipped_rows,
        },
        model_id=model.model_id,
        status=QueryStatus.pending,
    )
    db.add(query)
    db.commit()
    db.refresh(query)

    background_tasks.add_task(
        run_csv_job,
        query.query_id,
        rows,
        skipped_rows=skipped_rows,
    )

    return QueryAcceptedResponse(
        query_id=query.query_id,
        status=QueryStatus.pending,
    )


@router.post(
    "/keyword",
    response_model=QueryAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_keyword_query(
    data: KeywordQueryRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QueryAcceptedResponse:
    try:
        model = get_active_model(db)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    try:
        get_predictor(model.model_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    query = SearchQuery(
        user_id=current_user.user_id,
        type=QueryType.keyword,
        keyword=data.keyword,
        params={"limit": data.limit, "time_range": data.time_range},
        model_id=model.model_id,
        status=QueryStatus.pending,
    )
    db.add(query)
    db.commit()
    db.refresh(query)

    background_tasks.add_task(run_keyword_job, query.query_id)

    return QueryAcceptedResponse(
        query_id=query.query_id,
        status=QueryStatus.pending,
    )


@router.get("/{query_id}/posts", response_model=PostListResponse)
def list_query_posts(
    query_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    label: SentimentLabel | None = None,
) -> PostListResponse:
    query = db.scalar(
        select(SearchQuery).where(
            SearchQuery.query_id == query_id,
            SearchQuery.user_id == current_user.user_id,
        )
    )
    if query is None:
        raise HTTPException(status_code=404, detail="Query not found")
    if query.model_id is None:
        return PostListResponse(items=[], total=0)

    filters = [
        QueryPost.query_id == query_id,
        Prediction.model_id == query.model_id,
    ]
    if label is not None:
        filters.append(Prediction.sentiment == label)

    total = db.scalar(
        select(func.count(Prediction.prediction_id))
        .select_from(QueryPost)
        .join(
            Prediction,
            Prediction.post_id == QueryPost.post_id,
        )
        .where(*filters)
    )

    rows = db.execute(
        select(Post, Model, Prediction)
        .join(QueryPost, QueryPost.post_id == Post.post_id)
        .join(
            Prediction,
            and_(
                Prediction.post_id == Post.post_id,
                Prediction.model_id == query.model_id,
            ),
        )
        .join(Model, Model.model_id == Prediction.model_id)
        .where(*filters)
        .order_by(Post.post_date.desc().nullslast(), Post.post_id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return PostListResponse(
        items=[
            PostWithPredictionResponse(
                post_id=post.post_id,
                text=post.text,
                author=post.author,
                subreddit=post.subreddit,
                url=post.url,
                post_date=post.post_date,
                prediction={
                    "model": model.name,
                    "label": prediction.sentiment,
                    "confidence": float(prediction.confidence),
                    "probabilities": {
                        SentimentLabel.negative: float(prediction.prob_negative),
                        SentimentLabel.neutral: float(prediction.prob_neutral),
                        SentimentLabel.positive: float(prediction.prob_positive),
                    },
                },
            )
            for post, model, prediction in rows
        ],
        total=total or 0,
    )


@router.get("/{query_id}/export")
def export_query_csv(
    query_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    query = db.scalar(
        select(SearchQuery).where(
            SearchQuery.query_id == query_id,
            SearchQuery.user_id == current_user.user_id,
        )
    )
    if query is None:
        raise HTTPException(status_code=404, detail="Query not found")

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "text",
            "label",
            "confidence",
            "prob_negative",
            "prob_neutral",
            "prob_positive",
            "post_date",
            "author",
            "subreddit",
            "url",
        ]
    )

    if query.model_id is not None:
        rows = db.execute(
            select(Post, Prediction)
            .join(QueryPost, QueryPost.post_id == Post.post_id)
            .join(
                Prediction,
                and_(
                    Prediction.post_id == Post.post_id,
                    Prediction.model_id == query.model_id,
                ),
            )
            .where(QueryPost.query_id == query_id)
            .order_by(Post.post_date.desc().nullslast(), Post.post_id.desc())
        ).all()

        for post, prediction in rows:
            writer.writerow(
                [
                    post.text,
                    prediction.sentiment.value,
                    prediction.confidence,
                    prediction.prob_negative,
                    prediction.prob_neutral,
                    prediction.prob_positive,
                    post.post_date.isoformat() if post.post_date else "",
                    post.author or "",
                    post.subreddit or "",
                    post.url or "",
                ]
            )

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="sentiboard_{query_id}.csv"'
        },
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
