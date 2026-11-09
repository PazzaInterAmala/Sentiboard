"""Main model: fine-tuned distilbert-base-uncased, 3 classes.

Artifact folder layout:
    config.json, model.safetensors, tokenizer files - output of `save_pretrained`
    meta.json      - name, version, trained_at, hyperparameters (written by train_distilbert.py)
    metrics.json   - written by evaluate.py

Label mapping is stored in the model config (id2label = LABELS).
"""

import json
from pathlib import Path

from sentiboard_ml.predictor import LABELS, PredictionResult

BASE_MODEL = "distilbert-base-uncased"
MAX_LENGTH = 128
BATCH_SIZE = 32
META_FILE = "meta.json"


class DistilBertPredictor:
    name = "distilbert"

    def __init__(self, model, tokenizer, version: str = "1.0", device: str | None = None):
        import torch

        labels = [model.config.id2label[i] for i in range(model.config.num_labels)]
        if labels != list(LABELS):
            raise ValueError(f"Model labels {labels} do not match LABELS {LABELS}")
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = model.to(self.device).eval()
        self.tokenizer = tokenizer
        self.version = version

    @classmethod
    def load(cls, path: str, device: str | None = None) -> "DistilBertPredictor":
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        path = Path(path)
        meta = json.loads((path / META_FILE).read_text()) if (path / META_FILE).exists() else {}
        tokenizer = AutoTokenizer.from_pretrained(path)
        model = AutoModelForSequenceClassification.from_pretrained(path)
        return cls(model, tokenizer, version=meta.get("version", "1.0"), device=device)

    def save(self, path: str, meta: dict | None = None) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(path)
        self.tokenizer.save_pretrained(path)
        meta = {"name": self.name, "version": self.version, **(meta or {})}
        (path / META_FILE).write_text(json.dumps(meta, indent=2))

    def predict(self, texts: list[str]) -> list[PredictionResult]:
        import torch

        results = []
        for start in range(0, len(texts), BATCH_SIZE):
            batch = self.tokenizer(
                texts[start : start + BATCH_SIZE],
                truncation=True,
                max_length=MAX_LENGTH,
                padding=True,
                return_tensors="pt",
            ).to(self.device)
            with torch.no_grad():
                probs = torch.softmax(self.model(**batch).logits.float(), dim=-1)
            results.extend(PredictionResult.from_probs(row) for row in probs.cpu().tolist())
        return results
