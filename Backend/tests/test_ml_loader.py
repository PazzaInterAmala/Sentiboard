from pathlib import Path

import pytest

from app.ml import loader
from app.models.model import Model


class FakePredictor:
    name = "fake"
    version = "1.0"

    def predict(self, texts: list[str]) -> list:
        return []


class FakeScalars:
    def __init__(self, models: list[Model]):
        self.models = models

    def all(self) -> list[Model]:
        return self.models


class FakeSession:
    def __init__(self, models: list[Model]):
        self.models = models

    def scalars(self, statement) -> FakeScalars:
        return FakeScalars(self.models)


def test_load_registered_models_uses_expected_paths_and_registers_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    models = [
        Model(model_id=1, name="baseline", version="1.0"),
        Model(model_id=2, name="distilbert", version="1.0"),
    ]
    (tmp_path / "baseline-1.0").mkdir()
    (tmp_path / "distilbert-1.0-onnx-int8").mkdir()
    calls: list[tuple[str, str]] = []
    registered: dict[int, FakePredictor] = {}
    preprocessors = []

    def predictor_loader(name: str, path: str) -> FakePredictor:
        calls.append((name, path))
        return FakePredictor()

    monkeypatch.setattr(
        loader,
        "register_predictor",
        lambda model_id, predictor: registered.setdefault(model_id, predictor),
    )
    monkeypatch.setattr(loader, "register_preprocessor", preprocessors.append)

    loader.load_registered_models(
        FakeSession(models),
        tmp_path,
        predictor_loader=predictor_loader,
    )

    assert calls == [
        ("baseline", str(tmp_path / "baseline-1.0")),
        ("distilbert", str(tmp_path / "distilbert-1.0-onnx-int8")),
    ]
    assert set(registered) == {1, 2}
    assert len(preprocessors) == 1
    assert callable(preprocessors[0])


def test_load_registered_models_rejects_empty_database(tmp_path: Path):
    with pytest.raises(LookupError, match="No models are configured in the database"):
        loader.load_registered_models(
            FakeSession([]),
            tmp_path,
            predictor_loader=lambda *_: FakePredictor(),
        )


def test_load_registered_models_reports_missing_artifacts(tmp_path: Path):
    model = Model(model_id=1, name="baseline", version="1.0")

    with pytest.raises(FileNotFoundError, match="Artifacts for model baseline 1.0"):
        loader.load_registered_models(
            FakeSession([model]),
            tmp_path,
            predictor_loader=lambda *_: FakePredictor(),
        )


def test_load_registered_models_rejects_unsupported_model_name(tmp_path: Path):
    model = Model(model_id=1, name="unknown", version="1.0")

    with pytest.raises(ValueError, match="Unsupported model name: unknown"):
        loader.load_registered_models(
            FakeSession([model]),
            tmp_path,
            predictor_loader=lambda *_: FakePredictor(),
        )
