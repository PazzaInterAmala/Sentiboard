"""Dataset loading for training and evaluation.

Every loader returns {"train", "validation", "test"} DataFrames with columns:
    id, text (raw), clean_text, label (str), label_id (int, index in LABELS)

- GoEmotions (main): Reddit comments, 27 emotions mapped to 3 classes.
- TweetEval: tweets, 3 classes; used as an out-of-domain check.

Revisions are pinned so results stay reproducible if the datasets change on the Hub.
"""

from typing import TYPE_CHECKING

from sentiboard_ml.predictor import LABELS
from sentiboard_ml.preprocess import clean_text

if TYPE_CHECKING:
    import pandas as pd

SPLITS = ("train", "validation", "test")

GOEMOTIONS = ("google-research-datasets/go_emotions", "simplified")
GOEMOTIONS_REVISION = "add492243ff905527e67aeb8b80c082af02207c3"
TWEET_EVAL = ("cardiffnlp/tweet_eval", "sentiment")
TWEET_EVAL_REVISION = "b3a375baf0f409c77e6bc7aa35102b7b3534f8be"

# Google's own grouping (goemotions/data/sentiment_mapping.json) + neutral.
# "ambiguous" emotions (confusion, curiosity, realization, surprise) are not mapped.
GOEMOTIONS_SENTIMENT = {
    "positive": {
        "admiration", "amusement", "approval", "caring", "desire", "excitement",
        "gratitude", "joy", "love", "optimism", "pride", "relief",
    },
    "negative": {
        "anger", "annoyance", "disappointment", "disapproval", "disgust", "embarrassment",
        "fear", "grief", "nervousness", "remorse", "sadness",
    },
    "neutral": {"neutral"},
}  # fmt: skip
_EMOTION_TO_SENTIMENT = {e: s for s, emotions in GOEMOTIONS_SENTIMENT.items() for e in emotions}


def emotions_to_sentiment(emotions: list[str]) -> str | None:
    """Map a comment's GoEmotions labels to one sentiment.

    Returns None (drop the comment) if any emotion is ambiguous or the emotions
    belong to different sentiments, e.g. joy + sadness.
    """
    groups = {_EMOTION_TO_SENTIMENT.get(e) for e in emotions}
    if len(groups) != 1 or None in groups:
        return None
    return groups.pop()


def deduplicate(frames: dict[str, "pd.DataFrame"]) -> dict[str, "pd.DataFrame"]:
    """Remove duplicate texts (compared after clean_text).

    Within a split, a text with conflicting labels is dropped entirely, otherwise one copy
    is kept. Texts of validation/test are removed from train, so evaluation never sees
    training examples.
    """
    out = {}
    for split, df in frames.items():
        n_labels = df.groupby("clean_text")["label"].transform("nunique")
        out[split] = df[n_labels == 1].drop_duplicates("clean_text").reset_index(drop=True)
    held_out = set(out["validation"].clean_text) | set(out["test"].clean_text)
    train = out["train"]
    out["train"] = train[~train.clean_text.isin(held_out)].reset_index(drop=True)
    return out


def load_goemotions(dedup: bool = True) -> dict[str, "pd.DataFrame"]:
    """GoEmotions converted to 3-class sentiment (main training dataset)."""
    from datasets import load_dataset  # training-only dependency

    raw = load_dataset(*GOEMOTIONS, revision=GOEMOTIONS_REVISION)
    names = raw["train"].features["labels"].feature.names
    frames = {}
    for split in SPLITS:
        df = raw[split].to_pandas()
        df["label"] = df["labels"].map(lambda ids: emotions_to_sentiment([names[i] for i in ids]))
        df = df.dropna(subset=["label"]).drop(columns="labels")
        frames[split] = _finish(df)
    return deduplicate(frames) if dedup else frames


def load_tweet_eval(dedup: bool = True) -> dict[str, "pd.DataFrame"]:
    """TweetEval sentiment (out-of-domain evaluation, optional extra training data)."""
    from datasets import load_dataset  # training-only dependency

    raw = load_dataset(*TWEET_EVAL, revision=TWEET_EVAL_REVISION)
    frames = {}
    for split in SPLITS:
        df = raw[split].to_pandas()
        df["label"] = df["label"].map(lambda i: LABELS[i])
        df["id"] = [f"tweet_eval-{split}-{i}" for i in range(len(df))]
        frames[split] = _finish(df)
    return deduplicate(frames) if dedup else frames


DATASETS = {"goemotions": load_goemotions, "tweet_eval": load_tweet_eval}


def load(name: str = "goemotions", dedup: bool = True) -> dict[str, "pd.DataFrame"]:
    """Load a dataset by name (see DATASETS)."""
    if name not in DATASETS:
        raise ValueError(f"Unknown dataset {name!r}, expected one of {list(DATASETS)}")
    return DATASETS[name](dedup=dedup)


def _finish(df: "pd.DataFrame") -> "pd.DataFrame":
    df = df.copy()
    df["clean_text"] = df["text"].map(clean_text)
    df["label_id"] = df["label"].map(LABELS.index)
    return df[["id", "text", "clean_text", "label", "label_id"]].reset_index(drop=True)
