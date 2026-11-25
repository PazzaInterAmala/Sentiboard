from collections.abc import Callable
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.registry import (
    Predictor,
    register_predictor,
    register_preprocessor,
)
from app.models.model import Model


def _artifact_path(model: Model, model_dir: Path) -> Path:
    if model.name == "baseline":
        folder_name = f"baseline-{model.version}"
    elif model.name == "distilbert":
        folder_name = f"distilbert-{model.version}-onnx-int8"
    else:
        raise ValueError(f"Unsupported model name: {model.name}")

    return model_dir / folder_name


def load_registered_models(
    db: Session,
    model_dir: Path,
    predictor_loader: Callable[[str, str], Predictor] | None = None,
) -> None:
    if predictor_loader is None:
        from sentiboard_ml import clean_text, load_predictor

        predictor_loader = load_predictor
    else:
        from sentiboard_ml import clean_text

    models = db.scalars(select(Model).order_by(Model.model_id)).all()
    if not models:
        raise LookupError("No models are configured in the database")

    loaded_predictors: list[tuple[int, Predictor]] = []

    for model in models:
        artifact_path = _artifact_path(model, model_dir)
        if not artifact_path.is_dir():
            raise FileNotFoundError(
                f"Artifacts for model {model.name} {model.version} "
                f"were not found at {artifact_path}"
            )

        predictor = predictor_loader(model.name, str(artifact_path))
        loaded_predictors.append((model.model_id, predictor))

    for model_id, predictor in loaded_predictors:
        register_predictor(model_id, predictor)

    register_preprocessor(clean_text)
