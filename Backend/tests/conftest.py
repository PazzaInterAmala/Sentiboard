import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app


@pytest.fixture(scope="session")
def test_engine():
    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "TEST_DATABASE_URL is not configured. Set it before running pytest."
        )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    yield engine

    engine.dispose()


@pytest.fixture
def db_connection(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()

    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()


@pytest.fixture
def db(db_connection):
    with Session(
        bind=db_connection,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    ) as session:
        yield session


@pytest.fixture
def client(db_connection):
    def override_get_db():
        with Session(
            bind=db_connection,
            autoflush=False,
            join_transaction_mode="create_savepoint",
        ) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    was_testing = getattr(app.state, "testing", False)
    app.state.testing = True

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.state.testing = was_testing
