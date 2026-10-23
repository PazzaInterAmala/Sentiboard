import pytest

from sentiboard_ml.predictor import LABELS, PredictionResult, load_predictor


def test_labels_order_matches_tweet_eval():
    assert LABELS == ("negative", "neutral", "positive")


def test_from_probs_picks_max():
    result = PredictionResult.from_probs([0.87, 0.10, 0.03])
    assert result.label == "negative"
    assert result.confidence == pytest.approx(0.87)
    assert result.probabilities == {
        "negative": pytest.approx(0.87),
        "neutral": pytest.approx(0.10),
        "positive": pytest.approx(0.03),
    }


def test_from_probs_rejects_wrong_length():
    with pytest.raises(ValueError):
        PredictionResult.from_probs([0.5, 0.5])


def test_load_predictor_unknown_name():
    with pytest.raises(ValueError):
        load_predictor("gpt", "/nowhere")
