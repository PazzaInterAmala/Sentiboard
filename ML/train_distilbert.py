"""Fine-tune DistilBERT on GoEmotions (3-class) and save it to artifacts/distilbert-<version>/.

Evaluates on validation after every epoch and keeps the epoch with the best macro F1.

Usage:
    python train_distilbert.py --version 1.0 --epochs 3

Needs a GPU to finish in reasonable time (a 4 GB card is enough with fp16; Colab / Kaggle
work too). On CPU it runs, but takes hours.
"""

import argparse
import shutil
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score

from sentiboard_ml.data import GOEMOTIONS, GOEMOTIONS_REVISION, load
from sentiboard_ml.distilbert import BASE_MODEL, MAX_LENGTH, DistilBertPredictor
from sentiboard_ml.predictor import LABELS

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
SEED = 42


def to_dataset(df, tokenizer):
    from datasets import Dataset

    ds = Dataset.from_dict({"text": list(df.clean_text), "label": list(df.label_id)})
    return ds.map(
        lambda batch: tokenizer(batch["text"], truncation=True, max_length=MAX_LENGTH),
        batched=True,
        remove_columns=["text"],
    )


def compute_metrics(eval_pred) -> dict:
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "macro_f1": f1_score(labels, preds, average="macro"),
        "accuracy": float((preds == labels).mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="1.0")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    import torch
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        Trainer,
        TrainingArguments,
        set_seed,
    )

    set_seed(SEED)
    use_gpu = torch.cuda.is_available()
    print(f"device: {torch.cuda.get_device_name(0) if use_gpu else 'cpu'}")

    data = load("goemotions")
    train, val = data["train"], data["validation"]
    print(f"train={len(train)} validation={len(val)}")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(LABELS),
        id2label=dict(enumerate(LABELS)),
        label2id={label: i for i, label in enumerate(LABELS)},
    )

    out_dir = ARTIFACTS_DIR / f"distilbert-{args.version}"
    checkpoints_dir = ARTIFACTS_DIR / f"distilbert-{args.version}-checkpoints"
    training_args = TrainingArguments(
        output_dir=str(checkpoints_dir),
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        warmup_steps=0.1,  # float < 1 = ratio of total steps
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=1,
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        # similar lengths in a batch -> less padding, faster
        train_sampling_strategy="group_by_length",
        fp16=use_gpu,
        logging_steps=100,
        report_to="none",
        seed=SEED,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=to_dataset(train, tokenizer),
        eval_dataset=to_dataset(val, tokenizer),
        processing_class=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=compute_metrics,
    )
    trainer.train()
    evals = [log for log in trainer.state.log_history if "eval_macro_f1" in log]
    best = max(evals, key=lambda log: log["eval_macro_f1"])  # the model loaded at the end

    DistilBertPredictor(trainer.model, tokenizer, args.version).save(
        out_dir,
        meta={
            "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "dataset": f"{GOEMOTIONS[0]}:{GOEMOTIONS[1]}@{GOEMOTIONS_REVISION[:7]}",
            "train_size": len(train),
            "params": {
                "base_model": BASE_MODEL,
                "max_length": MAX_LENGTH,
                "epochs": args.epochs,
                "best_epoch": round(best["epoch"]),
                "lr": args.lr,
                "batch_size": args.batch_size,
                "warmup_ratio": 0.1,
                "weight_decay": 0.01,
                "seed": SEED,
            },
            "validation_macro_f1": round(best["eval_macro_f1"], 4),
        },
    )
    shutil.rmtree(checkpoints_dir, ignore_errors=True)
    print(f"validation macro F1={best['eval_macro_f1']:.4f} -> saved to {out_dir}")


if __name__ == "__main__":
    main()
