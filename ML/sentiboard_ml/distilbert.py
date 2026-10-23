"""Main model: fine-tuned distilbert-base-uncased, 3 classes.

Artifact folder layout: output of `save_pretrained` for model + tokenizer, plus metrics.json.
Label mapping is stored in the model config (id2label = LABELS).
"""

from sentiboard_ml.predictor import PredictionResult

BASE_MODEL = "distilbert-base-uncased"
MAX_LENGTH = 128
BATCH_SIZE = 32


class DistilBertPredictor:
    name = "distilbert"

    def __init__(self, model, tokenizer, version: str = "1.0"):
        self.model = model
        self.tokenizer = tokenizer
        self.version = version

    @classmethod
    def load(cls, path: str) -> "DistilBertPredictor":
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(path)
        model = AutoModelForSequenceClassification.from_pretrained(path)
        model.eval()
        return cls(model, tokenizer)

    def predict(self, texts: list[str]) -> list[PredictionResult]:
        # TODO(kirill): batches of BATCH_SIZE, tokenizer(truncation=True, max_length=MAX_LENGTH),
        # torch.no_grad(), softmax over logits, PredictionResult.from_probs per row.
        raise NotImplementedError
