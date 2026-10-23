import pandas as pd
import pytest

from sentiboard_ml.data import deduplicate, emotions_to_sentiment, load


@pytest.mark.parametrize(
    ("emotions", "expected"),
    [
        (["joy"], "positive"),
        (["joy", "gratitude"], "positive"),
        (["anger", "disgust"], "negative"),
        (["neutral"], "neutral"),
        (["joy", "sadness"], None),  # mixed groups
        (["surprise"], None),  # ambiguous
        (["joy", "curiosity"], None),  # positive + ambiguous
        (["neutral", "joy"], None),
    ],
)
def test_emotions_to_sentiment(emotions, expected):
    assert emotions_to_sentiment(emotions) == expected


def _df(rows):
    return pd.DataFrame(rows, columns=["clean_text", "label"])


def test_deduplicate():
    frames = {
        "train": _df(
            [
                ("same", "positive"),
                ("same", "positive"),  # exact duplicate -> one copy kept
                ("conflict", "positive"),
                ("conflict", "negative"),  # conflicting labels -> both dropped
                ("leak", "neutral"),  # also in test -> dropped from train
                ("unique", "negative"),
            ]
        ),
        "validation": _df([("val", "neutral")]),
        "test": _df([("leak", "neutral")]),
    }
    out = deduplicate(frames)
    assert sorted(out["train"].clean_text) == ["same", "unique"]
    assert list(out["test"].clean_text) == ["leak"]


def test_load_unknown_dataset():
    with pytest.raises(ValueError):
        load("imdb")
