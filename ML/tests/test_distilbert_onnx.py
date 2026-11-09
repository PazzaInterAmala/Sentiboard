"""ONNX export of a tiny random DistilBERT: same outputs as PyTorch, loadable without torch."""

import json

import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")
pytest.importorskip("onnxruntime")
pytest.importorskip("onnx")

from export_onnx import export
from sentiboard_ml.distilbert import BATCH_SIZE, DistilBertPredictor
from sentiboard_ml.distilbert_onnx import OnnxDistilBertPredictor
from sentiboard_ml.predictor import LABELS, load_predictor

TEXTS = ["i love it", "i hate a phone it it it", "a", "phone " * 200]  # incl. > MAX_LENGTH


@pytest.fixture(scope="module")
def torch_predictor(make_tiny_model, tiny_tokenizer, tmp_path_factory):
    path = tmp_path_factory.mktemp("distilbert-test")
    DistilBertPredictor(make_tiny_model(), tiny_tokenizer, version="test", device="cpu").save(
        str(path), meta={"trained_at": "2026-10-23T00:00:00+00:00"}
    )
    return path, DistilBertPredictor.load(str(path), device="cpu")


@pytest.fixture(scope="module")
def onnx_dirs(torch_predictor, tmp_path_factory):
    src, _ = torch_predictor
    out = tmp_path_factory.mktemp("onnx")
    return {
        "fp32": export(src, out / "fp32", quantize=False),
        "int8": export(src, out / "int8", quantize=True),
    }


def test_fp32_matches_pytorch(torch_predictor, onnx_dirs):
    _, pt = torch_predictor
    onnx = OnnxDistilBertPredictor.load(str(onnx_dirs["fp32"]))
    texts = TEXTS * BATCH_SIZE  # several batches with padding
    for a, b in zip(onnx.predict(texts), pt.predict(texts)):
        assert a.label == b.label
        assert a.probabilities == pytest.approx(b.probabilities, abs=1e-4)


def test_int8_returns_valid_results(onnx_dirs):
    results = OnnxDistilBertPredictor.load(str(onnx_dirs["int8"])).predict(TEXTS)
    assert len(results) == len(TEXTS)
    for r in results:
        assert list(r.probabilities) == list(LABELS)
        assert sum(r.probabilities.values()) == pytest.approx(1.0, abs=1e-5)


def test_predict_empty_list(onnx_dirs):
    assert OnnxDistilBertPredictor.load(str(onnx_dirs["int8"])).predict([]) == []


def test_load_predictor_picks_onnx_and_version(onnx_dirs):
    loaded = load_predictor("distilbert", str(onnx_dirs["int8"]))
    assert isinstance(loaded, OnnxDistilBertPredictor)
    assert loaded.version == "test-onnx-int8"
    meta = json.loads((onnx_dirs["int8"] / "meta.json").read_text())
    assert meta["source_version"] == "test"
    assert meta["trained_at"] == "2026-10-23T00:00:00+00:00"


def test_onnx_module_does_not_import_torch():
    # The server image should not need torch: check in a clean interpreter.
    import subprocess
    import sys

    code = (
        "import sys, sentiboard_ml.distilbert_onnx, sentiboard_ml.predictor; "
        "sys.exit(int('torch' in sys.modules or 'transformers' in sys.modules))"
    )
    assert subprocess.run([sys.executable, "-c", code], check=False).returncode == 0
