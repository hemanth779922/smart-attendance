import pytest
from fastapi.testclient import TestClient


def test_admin_only_endpoint_accessed_by_admin(client: TestClient, admin_token: str):
    """Admin accessing user management should succeed."""
    resp = client.get("/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200


def test_admin_only_endpoint_rejected_for_faculty(client: TestClient, faculty_token: str):
    """Faculty accessing user management must be forbidden (403)."""
    resp = client.get("/api/v1/users", headers={"Authorization": f"Bearer {faculty_token}"})
    assert resp.status_code == 403


def test_admin_only_endpoint_rejected_for_student(client: TestClient, student_token: str):
    """Student accessing user management must be forbidden (403)."""
    resp = client.get("/api/v1/users", headers={"Authorization": f"Bearer {student_token}"})
    assert resp.status_code == 403


def test_faculty_can_access_students(client: TestClient, faculty_token: str):
    """Faculty accessing student list should succeed."""
    resp = client.get("/api/v1/students", headers={"Authorization": f"Bearer {faculty_token}"})
    assert resp.status_code == 200
