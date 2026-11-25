import asyncio
from pathlib import Path

from app import main


class FakeSessionContext:
    def __init__(self):
        self.session = object()

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def test_lifespan_loads_models_from_database_on_startup(monkeypatch, tmp_path: Path):
    session_context = FakeSessionContext()
    calls = []

    monkeypatch.setattr(main, "SessionLocal", lambda: session_context)
    monkeypatch.setattr(main.settings, "model_dir", str(tmp_path))
    monkeypatch.setattr(
        main,
        "load_registered_models",
        lambda db, model_dir: calls.append((db, model_dir)),
    )
    monkeypatch.setattr(main.app.state, "testing", False, raising=False)

    async def run_lifespan():
        async with main.lifespan(main.app):
            pass

    asyncio.run(run_lifespan())

    assert calls == [(session_context.session, tmp_path)]


def test_lifespan_skips_model_loading_in_test_mode(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Model loader must not run in test mode")

    monkeypatch.setattr(main, "load_registered_models", fail_if_called)
    monkeypatch.setattr(main.app.state, "testing", True, raising=False)

    async def run_lifespan():
        async with main.lifespan(main.app):
            pass

    asyncio.run(run_lifespan())
