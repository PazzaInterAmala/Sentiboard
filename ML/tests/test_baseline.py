import pytest

from sentiboard_ml.baseline import BaselinePredictor, build_pipeline
from sentiboard_ml.predictor import LABELS, load_predictor

TEXTS = [
    "i love this, great job",
    "awesome, thank you so much",
    "this is terrible, i hate it",
    "worst thing ever, so angry",
    "the meeting is at 5 pm",
    "it is a phone with a screen",
] * 3
LABELS_ = ["positive", "positive", "negative", "negative", "neutral", "neutral"] * 3


@pytest.fixture(scope="module")
def predictor():
    return BaselinePredictor(build_pipeline().fit(TEXTS, LABELS_), version="test")


def test_predict_shape_and_probabilities(predictor):
    results = predictor.predict(["i love it", "i hate it", "it is a phone"])
    assert len(results) == 3
    for r in results:
        assert r.label in LABELS
        assert list(r.probabilities) == list(LABELS)
        assert sum(r.probabilities.values()) == pytest.approx(1.0)
        assert r.confidence == max(r.probabilities.values())


def test_predict_learns_obvious_cases(predictor):
    labels = [r.label for r in predictor.predict(["love it, great", "hate it, terrible"])]
    assert labels == ["positive", "negative"]


def test_predict_empty_list(predictor):
    assert predictor.predict([]) == []


def test_save_and_load_roundtrip(predictor, tmp_path):
    predictor.save(str(tmp_path), meta={"trained_at": "2026-10-23T00:00:00+00:00"})
    loaded = load_predictor("baseline", str(tmp_path))
    assert loaded.version == "test"
    texts = ["i love it", "i hate it"]
    assert loaded.predict(texts) == predictor.predict(texts)
