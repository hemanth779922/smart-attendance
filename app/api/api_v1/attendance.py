import time
import base64
import logging
from datetime import datetime, date, timezone
from typing import List, Optional
import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.session import get_db
from app.models.attendance import Attendance, AttendanceStatus
from app.models.student import Student
from app.models.subject import Subject, StudentSubject
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog
from app.schemas.attendance import (
    AttendanceResponse,
    AttendanceVerificationResult,
    VerificationStatus,
    MarkAttendanceRequest
)
from app.schemas.recognition import ChallengeResponse
from app.ai.low_light import detect_low_light, enhance_low_light, assess_face_quality
from app.ai.quality_assessment import assess_frame_quality
from app.ai.anti_spoofing import verify_anti_spoofing, generate_anti_spoof_challenge
from app.ai.face_engine import detect_faces, align_face, generate_face_embedding
from app.ai.vector_search import search_similar_face
from app.api.deps import require_roles, get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()


def decode_base64_image(image_base64: str) -> np.ndarray:
    """Decode base64 string to OpenCV BGR image."""
    try:
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        img_bytes = base64.b64decode(image_base64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Decoded frame is None")
        return img
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 image data: {str(e)}"
        )


@router.get("/challenge", response_model=ChallengeResponse)
def get_liveness_challenge():
    """Generate a randomized interactive anti-spoofing challenge."""
    return generate_anti_spoof_challenge()


@router.post("/mark", response_model=AttendanceVerificationResult)
def mark_attendance(
    req: MarkAttendanceRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.FACULTY])),
    db: Session = Depends(get_db)
):
    """
    7-Step Secure Attendance Pipeline with Atomic DB Transaction.
    
    1. Camera frame decoding & Quality Assessment
    2. Low-Light Detection & Selective Enhancement
    3. Face Detection & 5-Point Alignment
    4. Multi-Signal Anti-Spoofing & Liveness
    5. Face Embedding Generation & pgvector Similarity Search
    6. Confidence & Subject Enrollment Verification
    7. Atomic Database Transaction with Duplicate Attendance Prevention
    """
    t_start = time.time()
    latency = {}

    # Verify subject exists
    subject = db.query(Subject).filter(Subject.id == req.subject_id).first()
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    # Step 1: Decode image and assess frame quality
    t0 = time.time()
    frame = decode_base64_image(req.image_base64)
    quality_meta = assess_frame_quality(frame)
    latency["quality_check_ms"] = round((time.time() - t0) * 1000, 2)

    # Step 2: Low-light preprocessing
    t0 = time.time()
    is_low_light, _ = detect_low_light(frame)
    processed_frame = frame
    if is_low_light:
        processed_frame, _ = enhance_low_light(frame)
    latency["low_light_ms"] = round((time.time() - t0) * 1000, 2)

    # Step 3: Face Detection
    t0 = time.time()
    detected = detect_faces(processed_frame, apply_low_light_check=False)
    latency["detection_ms"] = round((time.time() - t0) * 1000, 2)

    if not detected:
        return AttendanceVerificationResult(
            status=VerificationStatus.FACE_NOT_DETECTED,
            message="No face detected in the frame. Please look directly into the camera.",
            quality_score=quality_meta["blur_score"],
            pipeline_latency_ms=latency
        )

    face_info = detected[0]
    face_crop = face_info["face_crop"]
    landmarks = face_info["landmarks"]

    # Face crop quality check
    face_quality = assess_face_quality(face_crop)
    if not face_quality["is_usable"]:
        return AttendanceVerificationResult(
            status=VerificationStatus.POOR_IMAGE_QUALITY,
            message=f"Image quality insufficient: {quality_meta['actionable_feedback']}",
            quality_score=face_quality["quality_score"],
            pipeline_latency_ms=latency
        )

    # Step 4: Anti-Spoofing & Liveness
    t0 = time.time()
    spoof_result = verify_anti_spoofing(
        face_crop=face_crop,
        challenge_token=req.challenge_token,
        detected_action=req.challenge_action
    )
    latency["anti_spoof_ms"] = round((time.time() - t0) * 1000, 2)

    if not spoof_result["is_live"]:
        if settings.AUDIT_LOG_ENABLED:
            db.add(AuditLog(
                user_id=current_user.id,
                action="SPOOF_ATTEMPT_REJECTED",
                details=f"Spoof score: {spoof_result['spoof_score']}, Challenge: {spoof_result['challenge']}"
            ))
            db.commit()

        return AttendanceVerificationResult(
            status=VerificationStatus.SPOOF_DETECTED,
            message="Anti-spoofing / liveness check failed. Please present a live, authentic face.",
            spoof_score=spoof_result["spoof_score"],
            confidence=spoof_result["confidence"],
            is_live=False,
            challenge_passed=spoof_result["signals"].get("challenge_passed", False),
            quality_score=face_quality["quality_score"],
            pipeline_latency_ms=latency
        )

    # Step 5: Feature Embedding & Alignment
    t0 = time.time()
    aligned_face = align_face(face_crop, landmarks)
    embedding_vec = generate_face_embedding(aligned_face)
    latency["embedding_ms"] = round((time.time() - t0) * 1000, 2)

    # Step 6: pgvector Vector Similarity Search
    t0 = time.time()
    match_result = search_similar_face(embedding_vec, db)
    latency["vector_search_ms"] = round((time.time() - t0) * 1000, 2)

    if not match_result or not match_result["recognized"]:
        return AttendanceVerificationResult(
            status=VerificationStatus.UNKNOWN_FACE if (match_result and match_result["similarity"] < 0.4) else VerificationStatus.LOW_CONFIDENCE,
            message=f"Face not recognized (Similarity: {match_result['similarity'] if match_result else 0.0:.2f} < Threshold {settings.FACE_MATCH_THRESHOLD}).",
            similarity=match_result["similarity"] if match_result else 0.0,
            confidence=match_result["confidence"] if match_result else 0.0,
            spoof_score=spoof_result["spoof_score"],
            quality_score=face_quality["quality_score"],
            pipeline_latency_ms=latency
        )

    student_id = match_result["student_id"]
    student = db.query(Student).filter(Student.id == student_id).first()

    # Step 7: Check if student is active & enrolled in this subject
    is_enrolled_in_subject = db.query(StudentSubject).filter(
        StudentSubject.student_id == student_id,
        StudentSubject.subject_id == req.subject_id
    ).first()

    if not is_enrolled_in_subject:
        return AttendanceVerificationResult(
            status=VerificationStatus.STUDENT_NOT_ENROLLED_IN_SUBJECT,
            message=f"Student {student.name} ({student.student_code}) is not enrolled in {subject.name}.",
            student_id=student.id,
            student_name=student.name,
            student_code=student.student_code,
            similarity=match_result["similarity"],
            confidence=match_result["confidence"],
            quality_score=face_quality["quality_score"],
            pipeline_latency_ms=latency
        )

    # Step 8: Duplicate Attendance Check & Atomic Transaction
    today = date.today()
    existing_attendance = db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.subject_id == req.subject_id,
        Attendance.session_date == today
    ).first()

    if existing_attendance:
        return AttendanceVerificationResult(
            status=VerificationStatus.ALREADY_MARKED,
            message=f"Attendance already marked for {student.name} today at {existing_attendance.session_time.strftime('%H:%M:%S')}.",
            student_id=student.id,
            student_name=student.name,
            student_code=student.student_code,
            similarity=match_result["similarity"],
            confidence=match_result["confidence"],
            spoof_score=spoof_result["spoof_score"],
            quality_score=face_quality["quality_score"],
            pipeline_latency_ms=latency
        )

    # Insert attendance record in transaction
    try:
        now_time = datetime.now().time()
        record = Attendance(
            student_id=student.id,
            subject_id=req.subject_id,
            session_date=today,
            session_time=now_time,
            status=AttendanceStatus.PRESENT,
            confidence=match_result["confidence"],
            spoof_score=spoof_result["spoof_score"],
            image_quality_score=face_quality["quality_score"],
            verified_by=current_user.id,
            verification_method="FACE_RECOGNITION"
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        latency["total_pipeline_ms"] = round((time.time() - t_start) * 1000, 2)

        resp_record = AttendanceResponse(
            id=record.id,
            student_id=student.id,
            subject_id=subject.id,
            session_date=record.session_date,
            session_time=record.session_time,
            status=record.status,
            confidence=record.confidence,
            spoof_score=record.spoof_score,
            image_quality_score=record.image_quality_score,
            verification_method=record.verification_method,
            created_at=record.created_at,
            student_name=student.name,
            student_code=student.student_code,
            subject_name=subject.name,
            subject_code=subject.code
        )

        return AttendanceVerificationResult(
            status=VerificationStatus.ATTENDANCE_MARKED,
            message=f"Attendance successfully marked for {student.name} ({student.student_code}) in {subject.name}.",
            student_id=student.id,
            student_name=student.name,
            student_code=student.student_code,
            similarity=match_result["similarity"],
            confidence=match_result["confidence"],
            spoof_score=spoof_result["spoof_score"],
            quality_score=face_quality["quality_score"],
            attendance_record=resp_record,
            pipeline_latency_ms=latency
        )
    except IntegrityError:
        db.rollback()
        return AttendanceVerificationResult(
            status=VerificationStatus.ALREADY_MARKED,
            message=f"Database constraint: Attendance already marked for {student.name} today.",
            student_id=student.id,
            student_name=student.name,
            student_code=student.student_code,
            pipeline_latency_ms=latency
        )


@router.get("/today", response_model=List[AttendanceResponse])
def get_today_attendance(
    subject_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List attendance records for today."""
    today = date.today()
    query = db.query(Attendance).join(Student).join(Subject).filter(Attendance.session_date == today)
    
    if subject_id:
        query = query.filter(Attendance.subject_id == subject_id)
    elif current_user.role == UserRole.FACULTY:
        query = query.filter(Subject.faculty_id == current_user.id)
    elif current_user.role == UserRole.STUDENT:
        query = query.filter(Attendance.student_id == current_user.id)

    records = query.order_by(Attendance.created_at.desc()).all()

    results = []
    for r in records:
        results.append(AttendanceResponse(
            id=r.id,
            student_id=r.student_id,
            subject_id=r.subject_id,
            session_date=r.session_date,
            session_time=r.session_time,
            status=r.status,
            confidence=r.confidence,
            spoof_score=r.spoof_score,
            image_quality_score=r.image_quality_score,
            verification_method=r.verification_method,
            created_at=r.created_at,
            student_name=r.student.name if r.student else None,
            student_code=r.student.student_code if r.student else None,
            subject_name=r.subject.name if r.subject else None,
            subject_code=r.subject.code if r.subject else None
        ))
    return results


@router.get("/history", response_model=List[AttendanceResponse])
def get_attendance_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    subject_id: Optional[int] = None,
    student_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieve historical attendance logs with date filtering."""
    query = db.query(Attendance).join(Student).join(Subject)

    if start_date:
        query = query.filter(Attendance.session_date >= start_date)
    if end_date:
        query = query.filter(Attendance.session_date <= end_date)
    if subject_id:
        query = query.filter(Attendance.subject_id == subject_id)
    if student_id:
        query = query.filter(Attendance.student_id == student_id)
    elif current_user.role == UserRole.STUDENT:
        query = query.filter(Attendance.student_id == current_user.id)

    records = query.order_by(Attendance.session_date.desc(), Attendance.session_time.desc()).all()

    results = []
    for r in records:
        results.append(AttendanceResponse(
            id=r.id,
            student_id=r.student_id,
            subject_id=r.subject_id,
            session_date=r.session_date,
            session_time=r.session_time,
            status=r.status,
            confidence=r.confidence,
            spoof_score=r.spoof_score,
            image_quality_score=r.image_quality_score,
            verification_method=r.verification_method,
            created_at=r.created_at,
            student_name=r.student.name if r.student else None,
            student_code=r.student.student_code if r.student else None,
            subject_name=r.subject.name if r.subject else None,
            subject_code=r.subject.code if r.subject else None
        ))
    return results


@router.get("/export")
def export_attendance_csv(
    subject_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.FACULTY])),
    db: Session = Depends(get_db)
):
    """Export attendance logs into downloadable CSV format."""
    query = db.query(Attendance).join(Student).join(Subject)
    if subject_id:
        query = query.filter(Attendance.subject_id == subject_id)
    if start_date:
        query = query.filter(Attendance.session_date >= start_date)
    if end_date:
        query = query.filter(Attendance.session_date <= end_date)

    records = query.order_by(Attendance.session_date.desc(), Attendance.session_time.desc()).all()

    csv_lines = ["ID,Student Code,Student Name,Subject Code,Subject Name,Date,Time,Status,Confidence,Spoof Score"]
    for r in records:
        s_code = r.student.student_code if r.student else ""
        s_name = f'"{r.student.name}"' if r.student else ""
        sub_code = r.subject.code if r.subject else ""
        sub_name = f'"{r.subject.name}"' if r.subject else ""
        csv_lines.append(f"{r.id},{s_code},{s_name},{sub_code},{sub_name},{r.session_date},{r.session_time},{r.status.value},{r.confidence:.2f},{r.spoof_score:.2f}")

    csv_data = "\n".join(csv_lines)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=attendance_export_{date.today()}.csv"}
    )
