"""Train the baseline on GoEmotions (3-class) and save it to artifacts/baseline-<version>/.

C (inverse regularisation strength) is picked by macro F1 on the validation split,
then the model trained with the best C is saved.

Usage:
    python train_baseline.py --version 1.0
    python train_baseline.py --version 1.0 --C 2     # skip the search
"""

import argparse
from datetime import UTC, datetime
from pathlib import Path

from sklearn.metrics import f1_score

from sentiboard_ml.baseline import TOKEN_PATTERN, BaselinePredictor, build_pipeline
from sentiboard_ml.data import GOEMOTIONS, GOEMOTIONS_REVISION, load

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
C_GRID = (0.5, 1.0, 2.0, 4.0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="1.0")
    parser.add_argument("--C", type=float, help="skip the search and use this C")
    args = parser.parse_args()

    data = load("goemotions")
    train, val = data["train"], data["validation"]
    print(f"train={len(train)} validation={len(val)}")

    best = None  # (val_f1, C, pipeline)
    for C in [args.C] if args.C else C_GRID:
        pipeline = build_pipeline(C).fit(train.clean_text, train.label)
        val_f1 = f1_score(val.label, pipeline.predict(val.clean_text), average="macro")
        print(f"C={C:<4} validation macro F1={val_f1:.4f}")
        if best is None or val_f1 > best[0]:
            best = (val_f1, C, pipeline)

    val_f1, C, pipeline = best
    out_dir = ARTIFACTS_DIR / f"baseline-{args.version}"
    BaselinePredictor(pipeline, args.version).save(
        out_dir,
        meta={
            "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "dataset": f"{GOEMOTIONS[0]}:{GOEMOTIONS[1]}@{GOEMOTIONS_REVISION[:7]}",
            "train_size": len(train),
            "params": {
                "C": C,
                "ngram_range": [1, 2],
                "min_df": 2,
                "token_pattern": TOKEN_PATTERN,
            },
            "validation_macro_f1": round(val_f1, 4),
        },
    )
    print(f"best C={C} (validation macro F1={val_f1:.4f}) -> saved to {out_dir}")


if __name__ == "__main__":
    main()
