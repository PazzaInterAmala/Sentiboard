"""Baseline model: TF-IDF (word 1-2 grams) + LogisticRegression.

Artifact folder layout:
    model.joblib   - fitted sklearn Pipeline
    meta.json      - name, version, trained_at, hyperparameters (written by train_baseline.py)
    metrics.json   - written by evaluate.py
"""

import json
from pathlib import Path

from sentiboard_ml.predictor import LABELS, PredictionResult

ARTIFACT_FILE = "model.joblib"
META_FILE = "meta.json"

# Words (with apostrophes, so "don't" stays one token) + every punctuation mark / emoji
# as its own token: "!", "?", "😍" carry sentiment. Beats sklearn's default pattern,
# which drops them, by ~0.4 macro F1 points on GoEmotions validation.
TOKEN_PATTERN = r"[\w']+|[^\w\s]"


def build_pipeline(C: float = 1.0):
    """Untrained sklearn Pipeline with the hyperparameters from the plan (§7.3)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2), min_df=2, sublinear_tf=True, token_pattern=TOKEN_PATTERN
                ),
            ),
            ("clf", LogisticRegression(C=C, class_weight="balanced", max_iter=2000)),
        ]
    )


class BaselinePredictor:
    name = "baseline"

    def __init__(self, pipeline, version: str = "1.0"):
        self.pipeline = pipeline
        self.version = version
        classes = list(pipeline.classes_)
        if sorted(classes) != sorted(LABELS):
            raise ValueError(f"Model classes {classes} do not match LABELS {LABELS}")
        # predict_proba columns follow pipeline.classes_; map them to LABELS order.
        self._columns = [classes.index(label) for label in LABELS]

    @classmethod
    def load(cls, path: str) -> "BaselinePredictor":
        import joblib

        path = Path(path)
        meta = json.loads((path / META_FILE).read_text()) if (path / META_FILE).exists() else {}
        return cls(joblib.load(path / ARTIFACT_FILE), version=meta.get("version", "1.0"))

    def save(self, path: str, meta: dict | None = None) -> None:
        import joblib

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, path / ARTIFACT_FILE)
        meta = {"name": self.name, "version": self.version, **(meta or {})}
        (path / META_FILE).write_text(json.dumps(meta, indent=2))

    def predict(self, texts: list[str]) -> list[PredictionResult]:
        if not texts:
            return []
        probs = self.pipeline.predict_proba(texts)[:, self._columns]
        return [PredictionResult.from_probs(row.tolist()) for row in probs]
