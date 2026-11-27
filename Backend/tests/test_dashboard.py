from datetime import UTC, datetime
from decimal import Decimal

from app.models.model import Model
from app.models.post import Post, PostSource
from app.models.prediction import Prediction, SentimentLabel
from app.models.query import QueryPost, QueryStatus, QueryType, SearchQuery
from app.services.dashboard import build_dashboard, keyword_words, top_words
from tests.test_queries_router import create_user

POSTS = [
    # text, label, post_date (None -> created_at is used)
    ("Love the iPhone camera, battery is great", "positive", datetime(2025, 7, 30)),
    ("iPhone camera is amazing, love it", "positive", datetime(2025, 7, 31)),
    ("The iPhone ships next week", "neutral", datetime(2025, 7, 31)),
    ("Battery died again, my iPhone is terrible", "negative", None),
]


def make_query(db, user_id, keyword="iphone", posts=POSTS, other_model_too=False):
    model = Model(name="dash-model", version="1.0")
    other = Model(name="dash-other", version="1.0")
    db.add_all([model, other])
    db.flush()
    query = SearchQuery(user_id=user_id, type=QueryType.keyword, keyword=keyword,
                        model_id=model.model_id, status=QueryStatus.done,
                        post_count=len(posts))  # fmt: skip
    db.add(query)
    db.flush()
    for i, (text, label, day) in enumerate(posts):
        post = Post(source=PostSource.reddit, external_id=f"dash-{i}", text=text,
                    clean_text=text.lower(),
                    post_date=day.replace(tzinfo=UTC) if day else None,
                    created_at=datetime(2025, 8, 1, 12, tzinfo=UTC))  # fmt: skip
        db.add(post)
        db.flush()
        db.add(QueryPost(query_id=query.query_id, post_id=post.post_id))
        db.add(_prediction(post, model, label))
        if other_model_too:  # predictions of another model must be ignored
            db.add(_prediction(post, other, "negative"))
    db.flush()
    return query


def _prediction(post, model, label):
    return Prediction(post_id=post.post_id, model_id=model.model_id,
                      sentiment=SentimentLabel(label), confidence=Decimal("0.9"),
                      prob_positive=Decimal("0.9") if label == "positive" else Decimal("0.05"),
                      prob_neutral=Decimal("0.9") if label == "neutral" else Decimal("0.05"),
                      prob_negative=Decimal("0.9") if label == "negative" else Decimal("0.05"))  # fmt: skip


def test_build_dashboard(db):
    user, _ = create_user(db, "dashuser")
    query = make_query(db, user.user_id, other_model_too=True)

    dashboard = build_dashboard(db, query)

    assert dashboard["counts"] == {"positive": 2, "neutral": 1, "negative": 1}
    assert dashboard["split"] == {"positive": 0.5, "neutral": 0.25, "negative": 0.25}
    assert dashboard["per_day"] == [
        {"date": "2025-07-30", "positive": 1, "neutral": 0, "negative": 0},
        {"date": "2025-07-31", "positive": 1, "neutral": 1, "negative": 0},
        {"date": "2025-08-01", "positive": 0, "neutral": 0, "negative": 1},
    ]
    positive = dashboard["top_words"]["positive"]
    assert positive[:2] == [
        {"word": "camera", "count": 2},
        {"word": "love", "count": 2},
    ]
    assert "iphone" not in {w["word"] for words in dashboard["top_words"].values()
                            for w in words}  # fmt: skip
    assert dashboard["top_words"]["negative"][0] == {"word": "battery", "count": 1}


def test_build_dashboard_without_posts_or_model(db):
    user, _ = create_user(db, "dashempty")
    query = make_query(db, user.user_id, posts=[])
    empty = build_dashboard(db, query)
    assert empty["counts"] == {"positive": 0, "neutral": 0, "negative": 0}
    assert empty["split"] == {"positive": 0.0, "neutral": 0.0, "negative": 0.0}
    assert empty["per_day"] == []

    query.model_id = None
    assert build_dashboard(db, query) == empty


def test_top_words_counts_each_text_once_and_drops_noise():
    texts = [
        "camera camera camera, i don't like it http url",
        "the camera is ok",
        "ok ok",
    ]
    assert top_words(texts) == [{"word": "camera", "count": 2}]
    assert top_words(["zebra apple", "apple zebra"], n=1) == [
        {"word": "apple", "count": 2}
    ]


def test_keyword_words_only_for_keyword_queries():
    keyword = SearchQuery(type=QueryType.keyword, keyword="iPhone 17")
    assert keyword_words(keyword) == {"iphone"}
    text = SearchQuery(type=QueryType.text, keyword="I love my iPhone")
    assert keyword_words(text) == set()


def test_top_words_hide_keyword_forms():
    texts = ["remote working remotely works", "carpool card cars", "workplace"]
    words = {w["word"] for w in top_words(texts, {"remote", "work", "car"})}
    assert words == {"carpool", "card", "workplace"}


def test_dashboard_route(client, db):
    user, token = create_user(db, "dashroute")
    query = make_query(db, user.user_id)

    response = client.get(
        f"/queries/{query.query_id}/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["query"]["query_id"] == query.query_id
    assert data["query"]["positive_share"] == 0.5
    assert data["counts"] == {"positive": 2, "neutral": 1, "negative": 1}
    assert len(data["per_day"]) == 3
    assert set(data["top_words"]) == {"positive", "neutral", "negative"}


def test_dashboard_route_hides_other_users_queries(client, db):
    owner, _ = create_user(db, "dashowner")
    _, other_token = create_user(db, "dashstranger")
    query = make_query(db, owner.user_id)

    response = client.get(
        f"/queries/{query.query_id}/dashboard",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 404
    assert client.get(f"/queries/{query.query_id}/dashboard").status_code == 401
