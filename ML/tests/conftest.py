"""Tiny random DistilBERT shared by the DistilBERT and ONNX tests (no downloads)."""

import pytest

from sentiboard_ml.predictor import LABELS

VOCAB = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", "i", "love", "hate", "it", "phone", "a"]


@pytest.fixture(scope="session")
def make_tiny_model():
    """Factory: make_tiny_model(id2label=None) -> random DistilBertForSequenceClassification."""
    torch = pytest.importorskip("torch")
    transformers = pytest.importorskip("transformers")

    def make(id2label=None):
        config = transformers.DistilBertConfig(
            vocab_size=len(VOCAB),
            dim=16,
            n_layers=1,
            n_heads=2,
            hidden_dim=32,
            num_labels=3,
            id2label=id2label or dict(enumerate(LABELS)),
        )
        torch.manual_seed(0)
        return transformers.DistilBertForSequenceClassification(config)

    return make


@pytest.fixture(scope="session")
def tiny_tokenizer(tmp_path_factory):
    transformers = pytest.importorskip("transformers")
    vocab_file = tmp_path_factory.mktemp("vocab") / "vocab.txt"
    vocab_file.write_text("\n".join(VOCAB))
    return transformers.DistilBertTokenizerFast(vocab_file=str(vocab_file))
