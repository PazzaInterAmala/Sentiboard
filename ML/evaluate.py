"""Evaluate a trained model and write metrics.json next to it.

Main metric: macro F1 on the GoEmotions test split; this and accuracy go to the
`models` table. TweetEval test is reported as an out-of-domain check.

Usage:
    python evaluate.py --model baseline --path artifacts/baseline-1.0
    python evaluate.py --model distilbert --path artifacts/distilbert-1.0 --cpu
"""

import argparse
import json
import time
from pathlib import Path

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from sentiboard_ml.data import load
from sentiboard_ml.predictor import LABELS, load_predictor
from sentiboard_ml.preprocess import clean_text

MAIN_DATASET = "goemotions"
EVAL_DATASETS = ("goemotions", "tweet_eval")

# Hand-picked hard cases (sarcasm, negation, slang): not a metric, a quick sanity check
# that is easy to show in the report. Expected labels are ours.
SPOT_CHECK = [
    ("Great, another delay from this airline", "negative"),
    ("not bad at all", "positive"),
    ("I don't love it", "negative"),
    ("I don't hate it", "positive"),
    ("this update is fire, devs cooked", "positive"),
    ("the new iPhone launches on Friday", "neutral"),
    ("Oh wonderful, my phone died again", "negative"),
    ("can't complain, works fine", "positive"),
    ("idk, it's ok i guess", "neutral"),
    ("worst purchase ever, total garbage", "negative"),
]


def evaluate(predictor, dataset: str) -> dict:
    test = load(dataset)["test"]
    start = time.perf_counter()
    preds = [r.label for r in predictor.predict(list(test.clean_text))]
    elapsed = time.perf_counter() - start
    report = classification_report(
        test.label, preds, labels=list(LABELS), output_dict=True, zero_division=0
    )
    return {
        "n": len(test),
        "accuracy": round(accuracy_score(test.label, preds), 4),
        "macro_f1": round(f1_score(test.label, preds, average="macro"), 4),
        "per_class_f1": {label: round(report[label]["f1-score"], 4) for label in LABELS},
        # rows = true label, columns = predicted label, both in LABELS order
        "confusion_matrix": confusion_matrix(test.label, preds, labels=list(LABELS)).tolist(),
        "seconds_per_1000": round(elapsed / len(test) * 1000, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=["baseline", "distilbert"])
    parser.add_argument("--path", required=True)
    parser.add_argument("--cpu", action="store_true", help="force CPU (as on the server)")
    args = parser.parse_args()

    path = Path(args.path)
    if args.cpu:
        import os

        # before torch is imported; "-1", not "": on Windows an empty value unsets the variable
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    predictor = load_predictor(args.model, str(path))
    meta_file = path / "meta.json"
    meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}

    results = {}
    for dataset in EVAL_DATASETS:
        results[dataset] = evaluate(predictor, dataset)
        r = results[dataset]
        print(
            f"{dataset:11} n={r['n']:6} accuracy={r['accuracy']:.4f} macro F1={r['macro_f1']:.4f}"
            f" ({r['seconds_per_1000']:.2f} s / 1000 texts)"
        )
        print(f"{'':11} per class F1: {r['per_class_f1']}")

    spot_check = []
    texts = [text for text, _ in SPOT_CHECK]
    for (text, expected), r in zip(SPOT_CHECK, predictor.predict([clean_text(t) for t in texts])):
        spot_check.append(
            {"text": text, "expected": expected, "predicted": r.label, "confidence": r.confidence}
        )
        mark = "ok " if r.label == expected else "BAD"
        print(f"{mark} {r.label:8} {r.confidence:.2f}  {text}")

    metrics = {
        "name": predictor.name,
        "version": predictor.version,
        "trained_at": meta.get("trained_at"),
        # the two numbers stored in the `models` table
        "accuracy": results[MAIN_DATASET]["accuracy"],
        "f1_score": results[MAIN_DATASET]["macro_f1"],
        "labels": list(LABELS),
        "test": results,
        "spot_check": spot_check,
    }
    (path / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"-> {path / 'metrics.json'}")


if __name__ == "__main__":
    main()
