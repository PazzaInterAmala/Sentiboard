import json
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.ml import registry
from app.ml.loader import find_artifacts, load_models
from app.models.model import Model
from app.models.user import User, UserRole
from app.services.auth import create_access_token

TEXTS = [
    "i love this, great job",
    "awesome, thank you so much",
    "this is terrible, i hate it",
    "worst thing ever, so angry",
    "the meeting is at 5 pm",
    "it is a phone with a screen",
] * 3
LABELS = ["positive", "positive", "negative", "negative", "neutral", "neutral"] * 3


@pytest.fixture(autouse=True)
def clean_registry(monkeypatch):
    # load_models writes to module-level registry state; keep tests isolated.
    monkeypatch.setattr(registry, "predictors", {})
    monkeypatch.setattr(registry, "preprocessor", None)


def write_baseline(
    path, version="test", accuracy=0.7, f1=0.69, trained_at="2026-10-23T13:35:47+00:00"
):
    from sentiboard_ml.baseline import BaselinePredictor, build_pipeline

    pipeline = build_pipeline().fit(TEXTS, LABELS)
    BaselinePredictor(pipeline, version=version).save(
        str(path), meta={"trained_at": trained_at}
    )
    (path / "metrics.json").write_text(
        json.dumps({"name": "baseline", "version": version, "trained_at": trained_at,
                    "accuracy": accuracy, "f1_score": f1})
    )  # fmt: skip
    return path


def write_meta(path, name, version, f1=None, trained_at=None):
    path.mkdir(parents=True)
    (path / "meta.json").write_text(json.dumps({"name": name, "version": version}))
    if f1 is not None:
        metrics = {"accuracy": f1, "f1_score": f1, "trained_at": trained_at}
        (path / "metrics.json").write_text(json.dumps(metrics))
    return path


def test_find_artifacts_missing_dir(tmp_path):
    assert find_artifacts(tmp_path / "nope") == []


def test_find_artifacts_reads_meta_and_metrics(tmp_path):
    write_meta(tmp_path / "distilbert-1.0-onnx-int8", "distilbert", "1.0-onnx-int8",
               f1=0.76543, trained_at="2026-10-23T21:01:52+00:00")  # fmt: skip
    write_meta(tmp_path / "no-name", "", "1.0")
    (tmp_path / "not-a-model").mkdir()

    [artifact] = find_artifacts(tmp_path)
    assert (artifact.name, artifact.version) == ("distilbert", "1.0-onnx-int8")
    assert artifact.f1_score == Decimal("0.7654")
    assert artifact.trained_at.isoformat() == "2026-10-23T21:01:52+00:00"


def test_load_models_registers_and_activates(db, tmp_path):
    write_baseline(tmp_path / "baseline-test")

    [model] = load_models(db, tmp_path)

    row = db.scalar(
        select(Model).where(Model.name == "baseline", Model.version == "test")
    )
    assert row.model_id == model.model_id
    assert row.is_active
    assert row.accuracy == Decimal("0.7000")
    assert row.f1_score == Decimal("0.6900")
    assert registry.get_predictor(row.model_id).name == "baseline"
    assert registry.clean_text("  Check https://x.org NOW ") == "check url now"


def test_load_models_twice_updates_the_same_row(db, tmp_path):
    write_baseline(tmp_path / "baseline-test", f1=0.5)
    [first] = load_models(db, tmp_path)

    write_baseline(tmp_path / "baseline-test", f1=0.6)
    [second] = load_models(db, tmp_path)

    assert first.model_id == second.model_id
    rows = db.scalars(
        select(Model).where(Model.name == "baseline", Model.version == "test")
    ).all()
    assert len(rows) == 1
    assert rows[0].f1_score == Decimal("0.6000")


def test_active_model_preference_and_fallbacks(db, tmp_path, monkeypatch):
    # Real loading is tested above; here only the choice of the active model matters.
    import sentiboard_ml

    monkeypatch.setattr(sentiboard_ml, "load_predictor", lambda name, path: object())
    write_meta(tmp_path / "baseline-t", "baseline", "t", f1=0.70)
    write_meta(tmp_path / "distilbert-t", "distilbert", "t", f1=0.76)

    # No preference, nothing active yet -> best f1.
    load_models(db, tmp_path)
    assert _active(db) == ("distilbert", "t")

    # Explicit preference wins.
    load_models(db, tmp_path, active_model="baseline")
    assert _active(db) == ("baseline", "t")

    # No preference -> the current active model is kept (e.g. chosen by an admin).
    load_models(db, tmp_path)
    assert _active(db) == ("baseline", "t")

    # Unknown preference -> falls back to keeping the current one.
    load_models(db, tmp_path, active_model="gpt")
    assert _active(db) == ("baseline", "t")


def test_active_model_not_deployed_any_more_is_replaced(db, tmp_path, monkeypatch):
    import sentiboard_ml

    monkeypatch.setattr(sentiboard_ml, "load_predictor", lambda name, path: object())
    db.add(Model(name="old-model", version="0.1", is_active=True))
    db.flush()
    write_meta(tmp_path / "baseline-t", "baseline", "t", f1=0.70)

    load_models(db, tmp_path)

    assert _active(db) == ("baseline", "t")


def test_broken_model_is_skipped(db, tmp_path):
    write_baseline(tmp_path / "baseline-test")
    write_meta(tmp_path / "distilbert-broken", "distilbert", "broken")  # no weights

    loaded = load_models(db, tmp_path)

    assert [m.name for m in loaded] == ["baseline"]
    assert db.scalar(select(Model).where(Model.name == "distilbert")) is None


def test_no_models_does_not_touch_db(db, tmp_path):
    assert load_models(db, tmp_path / "empty") == []
    assert registry.preprocessor is not None  # clean_text is still available


def test_analyze_with_real_baseline(client, db, tmp_path):
    write_baseline(tmp_path / "baseline-test")
    load_models(db, tmp_path)

    user = User(username="mluser", email="mluser@example.com", password_hash="x",
                role=UserRole.user)  # fmt: skip
    db.add(user)
    db.flush()

    response = client.post(
        "/analyze",
        json={"text": "I love this, great job!", "compare": False},
        headers={"Authorization": f"Bearer {create_access_token(user)}"},
    )

    assert response.status_code == 200, response.text
    [result] = response.json()["results"]
    assert result["model"] == "baseline"
    assert result["label"] == "positive"
    assert sum(result["probabilities"].values()) == pytest.approx(1.0)


def _active(db):
    db.expire_all()
    model = db.scalar(select(Model).where(Model.is_active.is_(True)))
    return (model.name, model.version)
