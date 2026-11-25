"""Dashboard numbers for one query: sentiment split, sentiment per day, top words.

Everything is computed from the predictions of the model the query was run with
(`query.model_id`), on request; fine for the ≤ 5000 posts a query can have.
"""

import re
from collections import Counter
from datetime import date

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.post import Post
from app.models.prediction import Prediction, SentimentLabel
from app.models.query import QueryPost, QueryType, SearchQuery

TOP_WORDS = 10
MIN_WORD_LENGTH = 3

# Words that say nothing about a topic: the scikit-learn English list, "url"/"user"
# (what clean_text puts in place of links and usernames), Reddit/web noise and the
# halves of contractions ("don't" -> "don", "t").
STOP_WORDS = ENGLISH_STOP_WORDS | {
    "url", "user", "http", "https", "www", "com", "amp", "gt", "lt", "nbsp",
    "don", "didn", "doesn", "isn", "wasn", "aren", "weren", "haven", "hasn", "won",
    "wouldn", "couldn", "shouldn", "ain", "ive", "im", "youre", "thats",
    "dont", "doesnt", "didnt", "cant", "wont", "just", "like", "really", "got",
    "get", "gets", "going", "know", "think", "make", "lot", "thing", "things",
    "people", "way", "say", "said", "yeah", "yes", "deleted", "removed",
}  # fmt: skip

_WORD = re.compile(r"[a-z]+(?:'[a-z]+)*")

LABELS = [SentimentLabel.positive, SentimentLabel.neutral, SentimentLabel.negative]


def build_dashboard(db: Session, query: SearchQuery) -> dict:
    """{"split", "counts", "per_day", "top_words"} for `query` (see docs §6.2)."""
    if query.model_id is None:
        return _empty()

    rows = db.execute(
        select(
            Prediction.sentiment,
            func.date(func.coalesce(Post.post_date, Post.created_at)),
            Post.clean_text,
            Post.text,
        )
        .select_from(QueryPost)
        .join(Post, Post.post_id == QueryPost.post_id)
        .join(Prediction, Prediction.post_id == Post.post_id)
        .where(
            QueryPost.query_id == query.query_id,
            Prediction.model_id == query.model_id,
        )
    ).all()

    counts = Counter(label for label, _, _, _ in rows)
    total = len(rows)

    per_day: dict[date, Counter] = {}
    for label, day, _, _ in rows:
        per_day.setdefault(day, Counter())[label] += 1

    ignore = keyword_words(query)
    texts_by_label: dict[SentimentLabel, list[str]] = {label: [] for label in LABELS}
    for label, _, clean, text in rows:
        texts_by_label[label].append(clean if clean is not None else text.lower())

    return {
        "split": {
            label.value: (counts[label] / total if total else 0.0) for label in LABELS
        },
        "counts": {label.value: counts[label] for label in LABELS},
        "per_day": [
            {"date": day.isoformat(), **{lb.value: per_day[day][lb] for lb in LABELS}}
            for day in sorted(per_day)
        ],
        "top_words": {
            label.value: top_words(texts_by_label[label], ignore) for label in LABELS
        },
    }


def top_words(
    texts: list[str], ignore: set[str] = frozenset(), n: int = TOP_WORDS
) -> list[dict]:
    """The `n` words found in the most texts (a word counts once per text, so one long
    post repeating a word cannot dominate). Ties: alphabetical."""
    counter = Counter()
    for text in texts:
        counter.update(
            {
                word
                for word in _WORD.findall(text)
                if len(word) >= MIN_WORD_LENGTH
                and "'" not in word
                and word not in STOP_WORDS
                and not _is_keyword_form(word, ignore)
            }
        )
    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [{"word": word, "count": count} for word, count in ranked[:n]]


def keyword_words(query: SearchQuery) -> set[str]:
    """Words of the searched keyword: every post contains them, so they (and their forms,
    see _is_keyword_form) are not shown."""
    if query.type != QueryType.keyword or not query.keyword:
        return set()
    return set(_WORD.findall(query.keyword.lower()))


def _is_keyword_form(word: str, keyword_words: set[str]) -> bool:
    """ "iphone" hides "iphones"; "remote work" also hides "remotely", "working"
    (a keyword word of 4+ letters plus up to 3 more letters)."""
    return any(
        word == kw
        or word == kw + "s"
        or (len(kw) >= 4 and word.startswith(kw) and len(word) - len(kw) <= 3)
        for kw in keyword_words
    )


def _empty() -> dict:
    return {
        "split": {label.value: 0.0 for label in LABELS},
        "counts": {label.value: 0 for label in LABELS},
        "per_day": [],
        "top_words": {label.value: [] for label in LABELS},
    }
