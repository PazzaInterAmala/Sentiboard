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
│   └── distilbert.py     # fine-tuned distilbert-base-uncased
├── train_baseline.py
├── train_distilbert.py
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

The backend installs only runtime deps: `pip install -e ../ML`.

## Using it from the backend

```python
from sentiboard_ml import clean_text, load_predictor

model = load_predictor("baseline", "/opt/models/baseline-1.0")
results = model.predict([clean_text("Great, another delay from this airline")])
results[0].label, results[0].confidence, results[0].probabilities
```

## Workflow

1. `python train_baseline.py --version 1.0`
2. `python train_distilbert.py --version 1.0` (GPU: Colab / Kaggle)
3. `python evaluate.py --model <name> --path artifacts/<name>-<version>`
4. Upload `artifacts/<name>-<version>/` to the Hugging Face Hub model repo.
