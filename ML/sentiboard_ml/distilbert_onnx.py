"""DistilBERT exported to ONNX and int8-quantized: the model the server runs.

Needs only onnxruntime + tokenizers + numpy (no torch / transformers), so it fits
the 512 MB RAM of Render Free/Starter. Created from a trained DistilBERT artifact
by export_onnx.py.

Artifact folder layout:
    model.onnx      - int8 dynamically quantized graph: (input_ids, attention_mask) -> logits
    tokenizer.json  - the same fast tokenizer the model was trained with
    config.json     - copied from the source model (id2label)
    meta.json       - name, version, source model, export params
    metrics.json    - written by evaluate.py
"""

import json
from pathlib import Path

import numpy as np

from sentiboard_ml.distilbert import BATCH_SIZE, MAX_LENGTH
from sentiboard_ml.predictor import LABELS, PredictionResult

ONNX_FILE = "model.onnx"
TOKENIZER_FILE = "tokenizer.json"
CONFIG_FILE = "config.json"
META_FILE = "meta.json"


def _softmax(logits: np.ndarray) -> np.ndarray:
    exp = np.exp(logits - logits.max(axis=-1, keepdims=True))
    return exp / exp.sum(axis=-1, keepdims=True)


class OnnxDistilBertPredictor:
    name = "distilbert"

    def __init__(self, session, tokenizer, id2label: dict, version: str = "1.0"):
        labels = [id2label[str(i)] for i in range(len(id2label))]
        if labels != list(LABELS):
            raise ValueError(f"Model labels {labels} do not match LABELS {LABELS}")
        self.session = session
        self.tokenizer = tokenizer
        self.version = version

    @classmethod
    def load(cls, path: str, threads: int | None = None) -> "OnnxDistilBertPredictor":
        import onnxruntime as ort
        from tokenizers import Tokenizer

        path = Path(path)
        meta = json.loads((path / META_FILE).read_text()) if (path / META_FILE).exists() else {}
        config = json.loads((path / CONFIG_FILE).read_text())

        tokenizer = Tokenizer.from_file(str(path / TOKENIZER_FILE))
        tokenizer.enable_truncation(max_length=MAX_LENGTH)
        tokenizer.enable_padding(pad_id=config.get("pad_token_id", 0), pad_token="[PAD]")

        options = ort.SessionOptions()
        if threads:
            options.intra_op_num_threads = threads
        session = ort.InferenceSession(
            str(path / ONNX_FILE), options, providers=["CPUExecutionProvider"]
        )
        return cls(session, tokenizer, config["id2label"], version=meta.get("version", "1.0"))

    def predict(self, texts: list[str]) -> list[PredictionResult]:
        results = []
        for start in range(0, len(texts), BATCH_SIZE):
            encodings = self.tokenizer.encode_batch(texts[start : start + BATCH_SIZE])
            inputs = {
                "input_ids": np.array([e.ids for e in encodings], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in encodings], dtype=np.int64),
            }
            (logits,) = self.session.run(["logits"], inputs)
            probs = _softmax(logits.astype(np.float64))
            results.extend(PredictionResult.from_probs(row) for row in probs.tolist())
        return results
