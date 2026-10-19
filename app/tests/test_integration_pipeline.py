import base64
from datetime import date
from typing import Tuple
import cv2
import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.student import Student
from app.models.subject import Subject, StudentSubject
from app.models.face_embedding import FaceEmbedding
from app.models.attendance import Attendance
from app.ai.face_engine import generate_face_embedding, align_face


def make_synthetic_face() -> Tuple[np.ndarray, str]:
    img = np.full((160, 160, 3), 150, dtype=np.uint8)
    cv2.circle(img, (50, 60), 10, (20, 20, 20), -1)
    cv2.circle(img, (110, 60), 10, (20, 20, 20), -1)
    cv2.circle(img, (80, 95), 8, (30, 30, 30), -1)
    cv2.ellipse(img, (80, 125), (28, 10), 0, 0, 180, (20, 20, 20), 4)
    _, buffer = cv2.imencode(".jpg", img)
    return img, base64.b64encode(buffer).decode("utf-8")


def test_complete_attendance_pipeline(client: TestClient, admin_token: str, db_session: Session):
    student = Student(
        student_code="INT001",
        name="Nikola Tesla",
        email="tesla@attendance.edu",
        department="Electrical Engineering",
        year=4,
        is_active=True
    )
    db_session.add(student)

    subject = Subject(
        code="EE401",
        name="Electromagnetism & AC Power",
        department="EE",
        semester=7,
        is_active=True
    )
    db_session.add(subject)
    db_session.commit()

    enrollment = StudentSubject(student_id=student.id, subject_id=subject.id)
    db_session.add(enrollment)
    db_session.commit()

    face_img, face_b64 = make_synthetic_face()
    aligned = align_face(face_img)
    emb_vec = generate_face_embedding(aligned)

    fe = FaceEmbedding(
        student_id=student.id,
        pose="frontal",
        quality_score=0.92,
        is_active=True
    )
    fe.set_embedding(emb_vec)
    db_session.add(fe)
    db_session.commit()

    chal_resp = client.get("/api/v1/attendance/challenge")
    assert chal_resp.status_code == 200
    chal_data = chal_resp.json()
    token = chal_data["challenge_token"]
    action = chal_data["challenge_type"]

    mark_resp = client.post("/api/v1/attendance/mark", json={
        "subject_id": subject.id,
        "image_base64": face_b64,
        "challenge_token": token,
        "challenge_action": action
    }, headers={"Authorization": f"Bearer {admin_token}"})

    assert mark_resp.status_code == 200
    res = mark_resp.json()
    assert res["status"] in ["ATTENDANCE_MARKED", "ALREADY_MARKED"]
    if res["status"] == "ATTENDANCE_MARKED":
        assert res["student_id"] == student.id

    second_chal = client.get("/api/v1/attendance/challenge").json()
    dup_resp = client.post("/api/v1/attendance/mark", json={
        "subject_id": subject.id,
        "image_base64": face_b64,
        "challenge_token": second_chal["challenge_token"],
        "challenge_action": second_chal["challenge_type"]
    }, headers={"Authorization": f"Bearer {admin_token}"})

    assert dup_resp.status_code == 200
    dup_res = dup_resp.json()
    assert dup_res["status"] == "ALREADY_MARKED"


def test_ip_webcam_attendance(client: TestClient, admin_token: str, db_session: Session, monkeypatch):
    """Verify phone IP webcam attendance connection and mark endpoint."""
    # 1. Test test endpoint
    test_res = client.get("/api/v1/attendance/ip-webcam/test?url=http://127.0.0.1:9999")
    assert test_res.status_code == 200
    assert test_res.json()["connected"] is False

    # 2. Test mark endpoint with mock phone frame
    face_img, _ = make_synthetic_face()
    from app.api.api_v1 import attendance as att_module
    monkeypatch.setattr(att_module, "fetch_ip_webcam_frame", lambda url: face_img)

    subject = Subject(
        code="CS101",
        name="Intro to Programming",
        department="CS",
        semester=1,
        is_active=True
    )
    db_session.add(subject)
    db_session.commit()

    mark_resp = client.post(
        "/api/v1/attendance/ip-webcam/mark",
        json={"subject_id": subject.id, "ip_url": "http://192.168.1.5:8080"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert mark_resp.status_code == 200
    res_data = mark_resp.json()
    assert "status" in res_data
    assert "message" in res_data

