"""Load trained models from MODEL_DIR at startup and register them for /analyze.

MODEL_DIR holds one folder per model, as produced by ML/ (see ML/README.md):

    MODEL_DIR/baseline-1.0/               meta.json, metrics.json, model.joblib
    MODEL_DIR/distilbert-1.0-onnx-int8/   meta.json, metrics.json, model.onnx, tokenizer.json, ...

For every folder with a meta.json: load the predictor, upsert its row in `models`
(name, version, accuracy, f1_score, trained_at from meta.json / metrics.json) and register
it in app.ml.registry under its model_id. A folder that fails to load is logged and skipped,
so one broken model does not take the API down.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.ml import registry
from app.models.model import Model

logger = logging.getLogger(__name__)

META_FILE = "meta.json"
METRICS_FILE = "metrics.json"


@dataclass(frozen=True)
class Artifact:
    path: Path
    name: str
    version: str
    accuracy: Decimal | None
    f1_score: Decimal | None
    trained_at: datetime | None


def find_artifacts(model_dir: str | Path) -> list[Artifact]:
    """Model folders in `model_dir` (sorted by folder name); [] if the directory is missing."""
    model_dir = Path(model_dir)
    if not model_dir.is_dir():
        return []

    artifacts = []
    for path in sorted(p for p in model_dir.iterdir() if (p / META_FILE).is_file()):
        meta = json.loads((path / META_FILE).read_text(encoding="utf-8"))
        metrics_file = path / METRICS_FILE
        metrics = (
            json.loads(metrics_file.read_text(encoding="utf-8"))
            if metrics_file.is_file()
            else {}
        )
        if not meta.get("name") or not meta.get("version"):
            logger.error("Skipping %s: meta.json has no name/version", path)
            continue
        trained_at = metrics.get("trained_at") or meta.get("trained_at")
        artifacts.append(
            Artifact(
                path=path,
                name=meta["name"],
                version=meta["version"],
                accuracy=_decimal(metrics.get("accuracy")),
                f1_score=_decimal(metrics.get("f1_score")),
                trained_at=datetime.fromisoformat(trained_at) if trained_at else None,
            )
        )
    return artifacts


def upsert_model(db: Session, artifact: Artifact) -> Model:
    """Insert or update the `models` row for this artifact (matched by name + version)."""
    model = db.scalar(
        select(Model).where(
            Model.name == artifact.name, Model.version == artifact.version
        )
    )
    if model is None:
        model = Model(name=artifact.name, version=artifact.version, is_active=False)
        db.add(model)
    model.accuracy = artifact.accuracy
    model.f1_score = artifact.f1_score
    model.trained_at = artifact.trained_at
    db.flush()
    return model


def choose_active(
    db: Session, loaded: list[Model], preferred_name: str = ""
) -> Model | None:
    """Make one loaded model active and return it.

    - `preferred_name` set (ACTIVE_MODEL, e.g. "distilbert"): the newest loaded model with
      that name becomes active.
    - otherwise the currently active model stays active if it is loaded (so a choice made
      later through the API survives restarts); if not, the loaded model with the best
      f1_score becomes active.
    """
    if not loaded:
        return None

    target = None
    if preferred_name:
        candidates = [m for m in loaded if m.name == preferred_name]
        if candidates:
            target = max(candidates, key=_newest_first_key)
        else:
            logger.warning(
                "ACTIVE_MODEL=%r is not among the loaded models", preferred_name
            )
    if target is None:
        target = next((m for m in loaded if m.is_active), None)
    if target is None:
        target = max(
            loaded, key=lambda m: (m.f1_score or Decimal(0), *_newest_first_key(m))
        )

    if not target.is_active:
        # Only one active row is allowed (unique partial index): clear the old one first.
        db.execute(
            update(Model).where(Model.is_active.is_(True)).values(is_active=False),
            execution_options={"synchronize_session": "fetch"},
        )
        db.flush()
        target.is_active = True
        db.flush()
    return target


def load_models(
    db: Session, model_dir: str | Path, active_model: str = ""
) -> list[Model]:
    """Load every model in `model_dir`, sync the `models` table and fill app.ml.registry.

    Returns the loaded models. With no models found the database is not touched, and
    /analyze answers 503 until models are deployed.
    """
    from sentiboard_ml import clean_text, load_predictor

    registry.register_preprocessor(clean_text)

    artifacts = find_artifacts(model_dir)
    if not artifacts:
        logger.warning("No models found in MODEL_DIR=%s", model_dir)
        return []

    loaded = []
    for artifact in artifacts:
        try:
            predictor = load_predictor(artifact.name, str(artifact.path))
        except Exception:
            logger.exception("Could not load model from %s", artifact.path)
            continue
        model = upsert_model(db, artifact)
        registry.register_predictor(model.model_id, predictor)
        loaded.append(model)
        logger.info(
            "Loaded model %s %s (model_id=%s)",
            model.name,
            model.version,
            model.model_id,
        )

    active = choose_active(db, loaded, active_model)
    db.commit()
    if active is not None:
        logger.info("Active model: %s %s", active.name, active.version)
    return loaded


def _decimal(value) -> Decimal | None:
    return None if value is None else Decimal(str(value)).quantize(Decimal("0.0001"))


def _newest_first_key(model: Model) -> tuple[float, int]:
    return (model.trained_at.timestamp() if model.trained_at else 0.0, model.model_id)
