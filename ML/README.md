# SentiBoard – ML

Sentiment models for SentiBoard: 3 classes (`negative`, `neutral`, `positive`).
Design decisions: [docs/IMPLEMENTATION_PLAN.md §7](../docs/IMPLEMENTATION_PLAN.md#7-ml).

## Layout

```
ML/
├── sentiboard_ml/        # importable package, used by the backend
│   ├── preprocess.py     # clean_text() – same for training and inference
│   ├── predictor.py      # LABELS, PredictionResult, Predictor, load_predictor()
│   ├── data.py           # load("goemotions" | "tweet_eval")
│   ├── baseline.py       # TF-IDF + LogisticRegression
│   ├── distilbert.py     # fine-tuned distilbert-base-uncased (PyTorch, for training)
│   └── distilbert_onnx.py # the same model as int8 ONNX (what the server runs)
├── train_baseline.py
├── train_distilbert.py
├── export_onnx.py        # DistilBERT -> ONNX int8
├── evaluate.py           # writes metrics.json for the `models` table
├── notebooks/            # EDA and experiments, not imported anywhere
├── tests/
└── artifacts/            # trained models, git-ignored
```

## Setup

```bash
cd ML
py -3.12 -m venv .venv
.venv\Scripts\activate          # Windows; on Linux/macOS: source .venv/bin/activate
pip install -e ".[train,dev]"
pytest
```

For training DistilBERT on an NVIDIA GPU, install the CUDA build of torch first
(the default wheel on Windows is CPU-only):

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

The backend installs only runtime deps: `pip install -e ../ML`.

## Using it from the backend

```python
from sentiboard_ml import clean_text, load_predictor

model = load_predictor("baseline", "/opt/models/baseline-1.0")
# or DistilBERT; a folder with model.onnx is loaded with onnxruntime (no torch needed)
model = load_predictor("distilbert", "/opt/models/distilbert-1.0-onnx-int8")
results = model.predict([clean_text("Great, another delay from this airline")])
results[0].label, results[0].confidence, results[0].probabilities
```

## Workflow

1. `python train_baseline.py --version 1.0`
2. `python train_distilbert.py --version 1.0` (GPU; a 4 GB card is enough with fp16)
3. `python export_onnx.py --path artifacts/distilbert-1.0` → `artifacts/distilbert-1.0-onnx-int8/`
4. `python evaluate.py --model <name> --path artifacts/<folder> --cpu`
5. Upload the folder that will be served (`baseline-1.0`, `distilbert-1.0-onnx-int8`) to the
   Hugging Face Hub model repo.

## Results

Macro F1 / accuracy on test splits. GoEmotions is the main metric (stored in the `models` table);
TweetEval is out-of-domain (tweets, different class balance).

| Model | GoEmotions macro F1 | GoEmotions acc | TweetEval macro F1 | Notes |
|---|---|---|---|---|
| baseline 1.0 | 0.709 | 0.719 | 0.484 | TF-IDF 1–2 grams + LogReg, C=2 |
| distilbert 1.0 | **0.767** | **0.777** | **0.553** | 3 epochs, lr 2e-5, best epoch 3; ~35 min on a GTX 1650 |

Per-class F1 on GoEmotions test (negative / neutral / positive):
baseline 0.64 / 0.69 / 0.80, distilbert 0.73 / 0.72 / 0.85.

### Serving DistilBERT: ONNX int8

The server runs DistilBERT as int8-quantized ONNX (`export_onnx.py`), with onnxruntime +
tokenizers only, no torch. Preliminary numbers on a laptop CPU (300 GoEmotions test texts,
on battery, so compare ratios, not absolute values):

| Variant | `model.onnx` / weights | Speed on CPU | Same label as PyTorch |
|---|---|---|---|
| baseline 1.0 | 2.5 MB | very fast | – |
| distilbert 1.0, PyTorch fp32 | 256 MB | ~45 texts/s | – |
| distilbert 1.0, ONNX fp32 | 256 MB | ~50 texts/s | 100% (identical probabilities) |
| distilbert 1.0, ONNX int8 | **64 MB** | **~85 texts/s** | 96.7% |

TODO: full test-set metrics of the int8 model (`evaluate.py --cpu`) and its RAM use,
which must fit the 512 MB of Render Free/Starter (plan §9).

Spot check (`SPOT_CHECK` in `evaluate.py`, 10 hard phrases): baseline 3/10, distilbert 5/10.
DistilBERT fixes negation ("I don't love it", "I don't hate it", "can't complain"), but both
models still read sarcasm as positive ("Great, another delay…", "Oh wonderful, my phone died
again") and miss slang ("devs cooked"). GoEmotions has few sarcastic examples, so this is a
known limitation to mention in the report.
