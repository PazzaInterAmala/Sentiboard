"""Fine-tune DistilBERT on GoEmotions (3-class) and save it to artifacts/distilbert-<version>/.

Usage:
    python train_distilbert.py --version 1.0 --epochs 3

Needs a GPU to finish in reasonable time (Colab / Kaggle are fine).
"""

import argparse
from pathlib import Path

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="1.0")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    out_dir = ARTIFACTS_DIR / f"distilbert-{args.version}"
    # TODO(kirill):
    #   1. data = load("goemotions"); tokenize clean_text with MAX_LENGTH
    #   2. AutoModelForSequenceClassification(BASE_MODEL, num_labels=3,
    #      id2label / label2id from LABELS)
    #   3. Trainer: eval on validation each epoch, keep best by macro F1
    #   4. save_pretrained(out_dir) for model and tokenizer
    raise NotImplementedError(f"would save to {out_dir}")


if __name__ == "__main__":
    main()
