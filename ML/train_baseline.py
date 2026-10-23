"""Train the baseline on GoEmotions (3-class) and save it to artifacts/baseline-<version>/.

Usage:
    python train_baseline.py --version 1.0
"""

import argparse
from pathlib import Path

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="1.0")
    args = parser.parse_args()

    out_dir = ARTIFACTS_DIR / f"baseline-{args.version}"
    # TODO(kirill):
    #   1. data = load("goemotions")
    #   2. pipeline = build_pipeline(); pipeline.fit(train.clean_text, train.label)
    #   3. BaselinePredictor(pipeline, args.version).save(out_dir)
    raise NotImplementedError(f"would save to {out_dir}")


if __name__ == "__main__":
    main()
