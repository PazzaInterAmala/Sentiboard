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
│   ├── distilbert_onnx.py # the same model as int8 ONNX (what the server runs)
│   └── reddit_index.py   # offline Reddit search (SQLite FTS5), used by keyword search
├── train_baseline.py
├── train_distilbert.py
├── export_onnx.py        # DistilBERT -> ONNX int8
├── evaluate.py           # writes metrics.json for the `models` table
├── build_reddit_index.py # Reddit dataset -> artifacts/reddit_posts.sqlite
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

The backend installs only runtime deps: `pip install -e ../ML` (numpy, scikit-learn, joblib,
onnxruntime, tokenizers; no torch). torch and transformers come with the `train` extra.


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
5. Upload the folders that are served (`baseline-1.0`, `distilbert-1.0-onnx-int8`) to the
   Hugging Face Hub: [KirillPo/sentiboard-models](https://huggingface.co/KirillPo/sentiboard-models).

### Get the trained models and the Reddit index

Both are public on the Hugging Face Hub, no token needed (`pip install huggingface_hub`):

```bash
hf download KirillPo/sentiboard-models --local-dir artifacts
hf download KirillPo/sentiboard-reddit-index reddit_posts.sqlite --repo-type dataset --local-dir artifacts
```

Then run the backend with `MODEL_DIR=../ML/artifacts` and
`REDDIT_INDEX_PATH=../ML/artifacts/reddit_posts.sqlite` (see `Backend/.env.example`).

## Results

Macro F1 / accuracy on test splits. GoEmotions is the main metric (stored in the `models` table);
TweetEval is out-of-domain (tweets, different class balance).

| Model | GoEmotions macro F1 | GoEmotions acc | TweetEval macro F1 | Notes |
|---|---|---|---|---|
| baseline 1.0 | 0.709 | 0.719 | 0.484 | TF-IDF 1–2 grams + LogReg, C=2 |
| distilbert 1.0 | **0.767** | **0.777** | 0.553 | 3 epochs, lr 2e-5, best epoch 3; ~35 min on a GTX 1650 |
| distilbert 1.0-onnx-int8 | 0.764 | 0.773 | **0.556** | what the server runs; ~12 s / 1000 texts on a laptop CPU |

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

On the full test sets int8 loses almost nothing: GoEmotions macro F1 0.764 vs 0.767,
TweetEval 0.556 vs 0.553 (table above). RAM: the backend with both models (baseline + int8
DistilBERT) uses ~330 MB in a Linux container limited to 512 MB, stable under load, so it fits
Render's 512 MB plan (§9).

Spot check (`SPOT_CHECK` in `evaluate.py`, 10 hard phrases): baseline 3/10, distilbert 5/10,
int8 4/10 (it flips "I don't hate it" to negative, 0.57).
DistilBERT fixes negation ("I don't love it", "I don't hate it", "can't complain"), but both
models still read sarcasm as positive ("Great, another delay…", "Oh wonderful, my phone died
again") and miss slang ("devs cooked"). GoEmotions has few sarcastic examples, so this is a
known limitation to mention in the report.

## Reddit keyword search (offline dataset)

The Reddit API is closed to new apps, so keyword search runs over a downloaded dataset:
[goldentraversy07/reddit_dataset_202507](https://huggingface.co/datasets/goldentraversy07/reddit_dataset_202507)
(MIT, posts and comments from thousands of subreddits, June-July 2025).

1. Download parquet files from the dataset's `data/` folder. We use `chunk_0` (June 9) and
   `chunk_12`-`chunk_29` (July 23-31): ~1.1 GB, ~2M rows.
2. `python build_reddit_index.py <folder with the parquet files>` →
   `artifacts/reddit_posts.sqlite`: keeps English texts of 30-1000 characters, drops bots,
   removed posts, duplicates and NSFW subreddits, then keeps all posts plus a random sample of
   comments, 200k rows in total (~35k posts, ~165k comments, 89 MB).
3. The backend reads the file from `REDDIT_INDEX_PATH` (`app/services/reddit.py`). It is
   published as the dataset
   [KirillPo/sentiboard-reddit-index](https://huggingface.co/datasets/KirillPo/sentiboard-reddit-index)
   and downloaded in the Docker build.

Search finds texts that contain every word of the keyword (case-insensitive, with stemming:
"phones" matches "phone"), best matches first; 5-60 ms per query. Limitations to mention in the
report: the posts are from summer 2025, not live; time ranges count back from the newest post
(July 31, 2025), so "week" is July 25-31; the dataset has no authors, links or scores.
