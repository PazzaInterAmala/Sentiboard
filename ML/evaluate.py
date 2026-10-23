"""Evaluate a trained model and write metrics.json.

Main metric: GoEmotions test split. TweetEval test is reported as an out-of-domain check.

Usage:
    python evaluate.py --model baseline --path artifacts/baseline-1.0

metrics.json is what fills the `models` table (accuracy, f1_score, trained_at).
"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=["baseline", "distilbert"])
    parser.add_argument("--path", required=True)
    args = parser.parse_args()

    # TODO(kirill):
    #   1. predictor = load_predictor(args.model, args.path)
    #   2. for ds in ("goemotions", "tweet_eval"): test = load(ds)["test"];
    #      preds = predictor.predict(list(test.clean_text))
    #   3. accuracy_score, f1_score(average="macro"), classification_report, confusion matrix
    #   4. write {name, version, accuracy, f1_score, trained_at} to <path>/metrics.json
    raise NotImplementedError(f"would evaluate {args.model} from {args.path}")


if __name__ == "__main__":
    main()
