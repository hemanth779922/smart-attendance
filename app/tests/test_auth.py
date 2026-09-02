import pytest
from fastapi.testclient import TestClient
from app.core.security import verify_password, get_password_hash, decode_token, create_access_token


def test_password_hashing():
    password = "MySecurePassword123!"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_flow():
    token = create_access_token(subject="user@test.edu", role="ADMIN", user_id=42)
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user@test.edu"
    assert payload["role"] == "ADMIN"
    assert payload["user_id"] == 42


def test_api_login_success(client: TestClient):
    resp = client.post("/api/v1/auth/login", json={
        "email": "testadmin@attendance.edu",
        "password": "Admin@12345"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["role"] == "ADMIN"


def test_api_login_invalid_password(client: TestClient):
    resp = client.post("/api/v1/auth/login", json={
        "email": "testadmin@attendance.edu",
        "password": "IncorrectPassword"
    })
    assert resp.status_code == 401


def test_api_auth_me(client: TestClient, admin_token: str):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "testadmin@attendance.edu"
    assert data["role"] == "ADMIN"


def test_unauthenticated_request(client: TestClient):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
