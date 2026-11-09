"""Common interface for all sentiment models.

The backend talks to models only through `Predictor` and `load_predictor`, so a model
can be swapped (baseline, DistilBERT, ONNX DistilBERT) without touching backend code.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# Fixed label order everywhere: model outputs, probability vectors, DB enum.
# Matches TweetEval ids: 0 = negative, 1 = neutral, 2 = positive.
LABELS: tuple[str, str, str] = ("negative", "neutral", "positive")


@dataclass(frozen=True)
class PredictionResult:
    label: str
    confidence: float
    probabilities: dict[str, float]  # keys = LABELS, values sum to ~1

    @classmethod
    def from_probs(cls, probs: list[float]) -> "PredictionResult":
        """Build a result from a probability vector in LABELS order."""
        if len(probs) != len(LABELS):
            raise ValueError(f"Expected {len(LABELS)} probabilities, got {len(probs)}")
        best = max(range(len(LABELS)), key=lambda i: probs[i])
        return cls(
            label=LABELS[best],
            confidence=float(probs[best]),
            probabilities={label: float(p) for label, p in zip(LABELS, probs)},
        )


class Predictor(Protocol):
    name: str
    version: str

    def predict(self, texts: list[str]) -> list[PredictionResult]:
        """Predict sentiment for already cleaned texts (see `clean_text`)."""
        ...


def load_predictor(name: str, path: str) -> Predictor:
    """Load a trained model from a local artifact folder.

    `name` is the `models.name` value in the DB: "baseline" or "distilbert".
    A "distilbert" folder with model.onnx (made by export_onnx.py) is loaded with
    onnxruntime and needs no torch; otherwise it is loaded with transformers.
    """
    if name == "baseline":
        from sentiboard_ml.baseline import BaselinePredictor

        return BaselinePredictor.load(path)
    if name == "distilbert" and (Path(path) / "model.onnx").exists():
        from sentiboard_ml.distilbert_onnx import OnnxDistilBertPredictor

        return OnnxDistilBertPredictor.load(path)
    if name == "distilbert":
        from sentiboard_ml.distilbert import DistilBertPredictor

        return DistilBertPredictor.load(path)
    raise ValueError(f"Unknown model name: {name!r}")
