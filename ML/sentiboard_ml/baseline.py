"""Baseline model: TF-IDF (word 1-2 grams) + LogisticRegression.

Artifact folder layout:
    model.joblib   - fitted sklearn Pipeline
    metrics.json   - written by evaluate.py
"""

from pathlib import Path

from sentiboard_ml.predictor import PredictionResult

ARTIFACT_FILE = "model.joblib"


class BaselinePredictor:
    name = "baseline"

    def __init__(self, pipeline, version: str = "1.0"):
        self.pipeline = pipeline
        self.version = version

    @classmethod
    def load(cls, path: str) -> "BaselinePredictor":
        import joblib

        return cls(joblib.load(Path(path) / ARTIFACT_FILE))

    def save(self, path: str) -> None:
        import joblib

        Path(path).mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, Path(path) / ARTIFACT_FILE)

    def predict(self, texts: list[str]) -> list[PredictionResult]:
        # TODO(kirill): predict_proba, reorder columns by pipeline.classes_ into LABELS order,
        # return PredictionResult.from_probs for each row.
        raise NotImplementedError


def build_pipeline():
    """Untrained sklearn Pipeline with the hyperparameters from the plan (§7.3)."""
    # TODO(kirill): TfidfVectorizer(ngram_range=(1, 2), min_df=2)
    #               + LogisticRegression(class_weight="balanced", max_iter=1000)
    raise NotImplementedError
