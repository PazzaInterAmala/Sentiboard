"""DistilBertPredictor on a tiny random model: checks the plumbing, not the quality."""

import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

from sentiboard_ml.distilbert import BATCH_SIZE, DistilBertPredictor
from sentiboard_ml.predictor import LABELS, load_predictor


@pytest.fixture(scope="module")
def predictor(make_tiny_model, tiny_tokenizer):
    return DistilBertPredictor(make_tiny_model(), tiny_tokenizer, version="test", device="cpu")


def test_predict_shape_and_probabilities(predictor):
    results = predictor.predict(["i love it", "i hate it", "a phone"])
    assert len(results) == 3
    for r in results:
        assert r.label in LABELS
        assert list(r.probabilities) == list(LABELS)
        assert sum(r.probabilities.values()) == pytest.approx(1.0, abs=1e-5)
        assert r.confidence == max(r.probabilities.values())


def test_batching_does_not_change_results(predictor):
    texts = ["i love it", "i hate a phone it it it"] * BATCH_SIZE  # 2 batches, padding
    batched = predictor.predict(texts)
    single = [predictor.predict([t])[0] for t in texts[:2]]
    assert len(batched) == len(texts)
    for b, s in zip(batched[:2], single):
        assert b.label == s.label
        assert b.probabilities == pytest.approx(s.probabilities, abs=1e-5)


def test_predict_empty_list(predictor):
    assert predictor.predict([]) == []


def test_wrong_label_order_is_rejected(make_tiny_model, tiny_tokenizer):
    wrong = {0: "positive", 1: "neutral", 2: "negative"}
    with pytest.raises(ValueError):
        DistilBertPredictor(make_tiny_model(wrong), tiny_tokenizer)


def test_save_and_load_roundtrip(predictor, tmp_path):
    predictor.save(str(tmp_path), meta={"trained_at": "2026-10-23T00:00:00+00:00"})
    loaded = load_predictor("distilbert", str(tmp_path))
    assert loaded.version == "test"
    texts = ["i love it", "i hate it"]
    for a, b in zip(loaded.predict(texts), predictor.predict(texts)):
        assert a.label == b.label
        assert a.probabilities == pytest.approx(b.probabilities, abs=1e-5)
