"""Export a trained DistilBERT artifact to ONNX and quantize it to int8 for the server.

Writes artifacts/distilbert-<version>-onnx-int8/ (see sentiboard_ml/distilbert_onnx.py).
Run evaluate.py on the result afterwards: quantization costs a little accuracy, and the
numbers in the `models` table must be those of the model that is actually deployed.

Usage:
    python export_onnx.py --path artifacts/distilbert-1.0
    python export_onnx.py --path artifacts/distilbert-1.0 --no-quantize   # fp32, for comparison
"""

import argparse
import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from sentiboard_ml.distilbert_onnx import CONFIG_FILE, META_FILE, ONNX_FILE, TOKENIZER_FILE

OPSET = 17


def export(src: Path, out: Path | None = None, quantize: bool = True) -> Path:
    """Export the DistilBERT artifact in `src`; returns the output folder."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    src = Path(src)
    meta = json.loads((src / META_FILE).read_text()) if (src / META_FILE).exists() else {}
    version = f"{meta.get('version', '1.0')}-onnx" + ("-int8" if quantize else "")
    out = Path(out) if out else src.parent / f"distilbert-{version}"
    out.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(src)
    # eager attention exports to plain ONNX ops; the default SDPA path may not
    model = AutoModelForSequenceClassification.from_pretrained(src, attn_implementation="eager")
    model.eval()

    class LogitsOnly(torch.nn.Module):
        def __init__(self, model):
            super().__init__()
            self.model = model

        def forward(self, input_ids, attention_mask):
            return self.model(input_ids=input_ids, attention_mask=attention_mask).logits

    dummy = tokenizer(
        ["a short text", "a somewhat longer text here"], padding=True, return_tensors="pt"
    )
    with tempfile.TemporaryDirectory() as tmp:
        fp32_path = Path(tmp) / ONNX_FILE
        torch.onnx.export(
            LogitsOnly(model),
            (dummy["input_ids"], dummy["attention_mask"]),
            str(fp32_path),
            input_names=["input_ids", "attention_mask"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch", 1: "sequence"},
                "attention_mask": {0: "batch", 1: "sequence"},
                "logits": {0: "batch"},
            },
            opset_version=OPSET,
            dynamo=False,
        )
        if quantize:
            from onnxruntime.quantization import QuantType, quantize_dynamic

            quantize_dynamic(fp32_path, out / ONNX_FILE, weight_type=QuantType.QInt8)
        else:
            shutil.copy(fp32_path, out / ONNX_FILE)

    for name in (TOKENIZER_FILE, CONFIG_FILE):
        shutil.copy(src / name, out / name)
    (out / META_FILE).write_text(
        json.dumps(
            {
                **meta,
                "name": "distilbert",
                "version": version,
                "source_version": meta.get("version"),
                "onnx": {
                    "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
                    "opset": OPSET,
                    "quantization": "dynamic int8 (weights)" if quantize else None,
                },
            },
            indent=2,
        )
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, help="trained DistilBERT artifact folder")
    parser.add_argument("--out", help="output folder (default: next to --path)")
    parser.add_argument("--no-quantize", action="store_true", help="keep fp32 weights")
    args = parser.parse_args()

    out = export(Path(args.path), args.out and Path(args.out), quantize=not args.no_quantize)
    size_mb = (out / ONNX_FILE).stat().st_size / 2**20
    print(f"-> {out} ({ONNX_FILE}: {size_mb:.0f} MB)")


if __name__ == "__main__":
    main()
