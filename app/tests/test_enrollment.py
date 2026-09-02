import base64
import cv2
import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.student import Student
from app.models.face_embedding import FaceEmbedding


def make_test_face_base64() -> str:
    img = np.full((160, 160, 3), 160, dtype=np.uint8)
    cv2.circle(img, (50, 60), 10, (30, 30, 30), -1)
    cv2.circle(img, (110, 60), 10, (30, 30, 30), -1)
    cv2.circle(img, (80, 95), 8, (40, 40, 40), -1)
    cv2.ellipse(img, (80, 125), (30, 12), 0, 0, 180, (20, 20, 20), 4)
    _, buffer = cv2.imencode(".jpg", img)
    return base64.b64encode(buffer).decode("utf-8")


def test_enrollment_sample_and_status(client: TestClient, admin_token: str, db_session: Session):
    # 1. Register student
    student_resp = client.post("/api/v1/students", json={
        "student_code": "ENR001",
        "name": "Claude Shannon",
        "email": "claude@attendance.edu",
        "department": "Information Theory",
        "year": 1
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert student_resp.status_code == 201
    student_id = student_resp.json()["id"]

    # 2. Check initial enrollment status
    status_resp = client.get(f"/api/v1/enrollment/status/{student_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert status_resp.status_code == 200
    assert status_resp.json()["is_enrolled"] is False
    assert status_resp.json()["sample_count"] == 0

    # 3. Submit enrollment sample
    b64_face = make_test_face_base64()
    sample_resp = client.post("/api/v1/enrollment/sample", json={
        "student_id": student_id,
        "image_base64": b64_face,
        "target_pose": "any"
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert sample_resp.status_code == 200
    data = sample_resp.json()
    assert "quality_score" in data
    assert "status" in data
    assert "samples_collected" in data
