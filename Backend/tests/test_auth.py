import pytest
from fastapi import HTTPException

from app.models.user import User, UserRole
from app.services.auth import require_admin


def register_user(client, username="testuser", email="test@example.com"):
    return client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "TestPassword123!",
        },
    )


def test_register_success(client):
    response = register_user(client)

    assert response.status_code == 201

    data = response.json()

    assert data["user"]["username"] == "testuser"
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["role"] == "user"
    assert "password_hash" not in data["user"]
    assert data["token"]


def test_register_duplicate_email(client):
    register_user(client)

    response = register_user(
        client,
        username="anotheruser",
        email="test@example.com",
    )

    assert response.status_code == 409


def test_register_duplicate_username(client):
    register_user(client)

    response = register_user(
        client,
        username="testuser",
        email="another@example.com",
    )

    assert response.status_code == 409


def test_login_success(client):
    register_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200
    assert response.json()["token"]


def test_login_wrong_password(client):
    register_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 401


def test_me_without_token(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_with_valid_token(client):
    register_response = register_user(client)
    token = register_response.json()["token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "testuser"
    assert response.json()["email"] == "test@example.com"


def test_require_admin_allows_admin():
    admin = User(
        username="admin",
        email="admin@example.com",
        password_hash="dummy",
        role=UserRole.admin,
    )

    result = require_admin(admin)

    assert result is admin


def test_require_admin_rejects_user():
    user = User(
        username="normaluser",
        email="user@example.com",
        password_hash="dummy",
        role=UserRole.user,
    )

    with pytest.raises(HTTPException) as exc_info:
        require_admin(user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Administrator privileges required"
