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


def test_get_query_returns_positive_share_for_completed_query(
    client: TestClient, db
):
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


def test_queries_requires_authentication(client: TestClient):
    response = client.get("/queries")

    assert response.status_code == 401
