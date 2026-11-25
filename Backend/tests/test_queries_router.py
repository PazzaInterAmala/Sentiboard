import csv
import io
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.models.model import Model
from app.models.post import Post, PostSource
from app.models.prediction import Prediction, SentimentLabel
from app.models.query import QueryPost, QueryStatus, QueryType, SearchQuery
from app.models.user import User, UserRole
from app.services.auth import create_access_token


def create_user(db, username: str) -> tuple[User, str]:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash="test-hash",
        role=UserRole.user,
    )
    db.add(user)
    db.flush()
    return user, create_access_token(user)


def create_query(db, user_id: int, keyword: str, status: QueryStatus):
    query = SearchQuery(
        user_id=user_id,
        type=QueryType.keyword,
        keyword=keyword,
        status=status,
        post_count=1 if status == QueryStatus.done else None,
    )
    db.add(query)
    db.flush()
    return query


def test_list_queries_returns_only_current_users_queries(client: TestClient, db):
    user, token = create_user(db, "queryowner")
    other_user, _ = create_user(db, "otherowner")
    first_query = create_query(db, user.user_id, "first", QueryStatus.pending)
    latest_query = create_query(db, user.user_id, "latest", QueryStatus.processing)
    create_query(db, other_user.user_id, "private", QueryStatus.pending)

    response = client.get(
        "/queries?page=1&page_size=1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 1
    assert data["items"][0]["query_id"] == latest_query.query_id
    assert data["items"][0]["keyword"] == "latest"
    assert data["items"][0]["positive_share"] is None

    second_page = client.get(
        "/queries?page=2&page_size=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second_page.status_code == 200
    assert second_page.json()["items"][0]["query_id"] == first_query.query_id


def test_get_query_returns_positive_share_for_completed_query(client: TestClient, db):
    user, token = create_user(db, "querydetail")
    model = Model(name="query-detail-model", version="1.0")
    db.add(model)
    db.flush()

    query = SearchQuery(
        user_id=user.user_id,
        type=QueryType.text,
        keyword="Great product",
        model_id=model.model_id,
        status=QueryStatus.done,
        post_count=1,
    )
    post = Post(
        source=PostSource.manual,
        text="Great product",
        clean_text="great product",
    )
    db.add_all([query, post])
    db.flush()
    db.add_all(
        [
            QueryPost(query_id=query.query_id, post_id=post.post_id),
            Prediction(
                post_id=post.post_id,
                model_id=model.model_id,
                sentiment=SentimentLabel.positive,
                confidence=0.9,
                prob_positive=0.9,
                prob_neutral=0.05,
                prob_negative=0.05,
            ),
        ]
    )
    db.flush()

    response = client.get(
        f"/queries/{query.query_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query_id"] == query.query_id
    assert data["type"] == "text"
    assert data["status"] == "done"
    assert data["positive_share"] == 1.0


def test_get_query_hides_another_users_query(client: TestClient, db):
    owner, _ = create_user(db, "queryprivate")
    requester, token = create_user(db, "queryrequester")
    query = create_query(db, owner.user_id, "private", QueryStatus.pending)

    response = client.get(
        f"/queries/{query.query_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert requester.user_id != owner.user_id
    assert response.status_code == 404
    assert response.json()["detail"] == "Query not found"


def test_list_query_posts_paginates_and_filters_by_sentiment(client: TestClient, db):
    user, token = create_user(db, "queryposts")
    model = Model(name="query-posts-model", version="1.0")
    other_model = Model(name="other-query-posts-model", version="1.0")
    db.add_all([model, other_model])
    db.flush()

    query = SearchQuery(
        user_id=user.user_id,
        type=QueryType.keyword,
        keyword="camera",
        model_id=model.model_id,
        status=QueryStatus.done,
    )
    posts = [
        Post(
            source=PostSource.reddit,
            external_id=f"t3-post-{index}",
            text=f"Post {index}",
            author=f"author-{index}",
            subreddit="photography",
            url=f"https://example.test/{index}",
            post_date=datetime(2026, 11, index, tzinfo=UTC),
        )
        for index in (1, 2, 3)
    ]
    db.add_all([query, *posts])
    db.flush()

    sentiments = [
        SentimentLabel.negative,
        SentimentLabel.positive,
        SentimentLabel.positive,
    ]
    for post, sentiment in zip(posts, sentiments, strict=True):
        db.add_all(
            [
                QueryPost(query_id=query.query_id, post_id=post.post_id),
                Prediction(
                    post_id=post.post_id,
                    model_id=model.model_id,
                    sentiment=sentiment,
                    confidence=0.8,
                    prob_positive=0.7,
                    prob_neutral=0.2,
                    prob_negative=0.1,
                ),
                Prediction(
                    post_id=post.post_id,
                    model_id=other_model.model_id,
                    sentiment=SentimentLabel.neutral,
                    confidence=0.9,
                    prob_positive=0.05,
                    prob_neutral=0.9,
                    prob_negative=0.05,
                ),
            ]
        )
    db.flush()

    response = client.get(
        f"/queries/{query.query_id}/posts?page=1&page_size=1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 1
    assert data["items"][0]["post_id"] == posts[2].post_id
    assert data["items"][0]["text"] == "Post 3"
    assert data["items"][0]["prediction"] == {
        "model": model.name,
        "label": "positive",
        "confidence": 0.8,
        "probabilities": {
            "negative": 0.1,
            "neutral": 0.2,
            "positive": 0.7,
        },
    }

    filtered_response = client.get(
        f"/queries/{query.query_id}/posts?label=negative",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert filtered_response.status_code == 200
    filtered_data = filtered_response.json()
    assert filtered_data["total"] == 1
    assert len(filtered_data["items"]) == 1
    assert filtered_data["items"][0]["post_id"] == posts[0].post_id


def test_list_query_posts_hides_another_users_query(client: TestClient, db):
    owner, _ = create_user(db, "querypostsowner")
    requester, token = create_user(db, "querypostsrequester")
    query = create_query(db, owner.user_id, "private", QueryStatus.done)

    response = client.get(
        f"/queries/{query.query_id}/posts",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert requester.user_id != owner.user_id
    assert response.status_code == 404
    assert response.json()["detail"] == "Query not found"


def test_list_query_posts_requires_authentication(client: TestClient):
    response = client.get("/queries/1/posts")

    assert response.status_code == 401


def test_list_query_posts_validates_pagination_and_label(client: TestClient, db):
    _, token = create_user(db, "querypostsvalidation")
    headers = {"Authorization": f"Bearer {token}"}
    invalid_page_response = client.get(
        "/queries/1/posts?page=0",
        headers=headers,
    )
    invalid_label_response = client.get(
        "/queries/1/posts?label=excited",
        headers=headers,
    )

    assert invalid_page_response.status_code == 422
    assert invalid_label_response.status_code == 422


def test_export_query_csv_contains_predictions_and_escapes_csv_values(
    client: TestClient, db
):
    user, token = create_user(db, "queryexport")
    model = Model(name="query-export-model", version="1.0")
    other_model = Model(name="other-query-export-model", version="1.0")
    db.add_all([model, other_model])
    db.flush()

    query = SearchQuery(
        user_id=user.user_id,
        type=QueryType.csv,
        file_name="reviews.csv",
        model_id=model.model_id,
        status=QueryStatus.done,
    )
    post = Post(
        source=PostSource.csv,
        text="Review, with\nnewline",
        clean_text="review newline",
        author="Alice, Smith",
        subreddit="photography",
        url="https://example.test/review",
        post_date=datetime(2026, 11, 20, tzinfo=UTC),
    )
    db.add_all([query, post])
    db.flush()
    db.add_all(
        [
            QueryPost(query_id=query.query_id, post_id=post.post_id),
            Prediction(
                post_id=post.post_id,
                model_id=model.model_id,
                sentiment=SentimentLabel.positive,
                confidence=0.9,
                prob_positive=0.9,
                prob_neutral=0.05,
                prob_negative=0.05,
            ),
            Prediction(
                post_id=post.post_id,
                model_id=other_model.model_id,
                sentiment=SentimentLabel.negative,
                confidence=0.8,
                prob_positive=0.1,
                prob_neutral=0.1,
                prob_negative=0.8,
            ),
        ]
    )
    db.flush()

    response = client.get(
        f"/queries/{query.query_id}/export",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="sentiboard_{query.query_id}.csv"'
    )

    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows == [
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
        ],
        [
            "Review, with\nnewline",
            "positive",
            "0.9000",
            "0.0500",
            "0.0500",
            "0.9000",
            "2026-11-20T00:00:00+00:00",
            "Alice, Smith",
            "photography",
            "https://example.test/review",
        ],
    ]


def test_export_query_csv_returns_header_for_query_without_predictions(
    client: TestClient, db
):
    user, token = create_user(db, "queryexportempty")
    query = SearchQuery(
        user_id=user.user_id,
        type=QueryType.csv,
        file_name="empty.csv",
        model_id=None,
        status=QueryStatus.done,
    )
    db.add(query)
    db.flush()

    response = client.get(
        f"/queries/{query.query_id}/export",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows == [
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
    ]


def test_export_query_csv_hides_another_users_query(client: TestClient, db):
    owner, _ = create_user(db, "queryexportowner")
    requester, token = create_user(db, "queryexportrequester")
    query = create_query(db, owner.user_id, "private", QueryStatus.done)

    response = client.get(
        f"/queries/{query.query_id}/export",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert requester.user_id != owner.user_id
    assert response.status_code == 404
    assert response.json()["detail"] == "Query not found"


def test_export_query_csv_requires_authentication(client: TestClient):
    response = client.get("/queries/1/export")

    assert response.status_code == 401


def test_queries_requires_authentication(client: TestClient):
    response = client.get("/queries")

    assert response.status_code == 401
