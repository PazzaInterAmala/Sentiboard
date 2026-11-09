from collections.abc import Callable
from typing import Protocol


class Predictor(Protocol):
    name: str
    version: str

    def predict(self, texts: list[str]) -> list: ...


predictors: dict[int, Predictor] = {}
preprocessor: Callable[[str], str] | None = None


def register_predictor(model_id: int, predictor: Predictor) -> None:
    predictors[model_id] = predictor


def get_predictor(model_id: int) -> Predictor:
    try:
        return predictors[model_id]
    except KeyError:
        raise LookupError(f"No predictor registered for model_id={model_id}")


def register_preprocessor(clean_text: Callable[[str], str]) -> None:
    global preprocessor
    preprocessor = clean_text


def clean_text(text: str) -> str:
    if preprocessor is None:
        raise LookupError("Text preprocessor is not configured")

    return preprocessor(text)


def get_available_model_ids() -> set[int]:
    return set(predictors.keys())
