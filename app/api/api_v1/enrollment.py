import base64
import logging
from typing import List
import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings
from app.db.session import get_db
from app.models.student import Student
from app.models.face_embedding import FaceEmbedding
from app.models.user import User, UserRole
from app.schemas.enrollment import (
    EnrollmentSampleRequest,
    EnrollmentSampleResponse,
    EnrollmentStatusResponse,
    ResetEnrollmentRequest,
    WebEnrollmentSubmitRequest,
    WebEnrollmentSubmitResponse
)
import os
import time
from app.ai.low_light import detect_low_light, enhance_low_light, assess_face_quality
from app.ai.quality_assessment import assess_frame_quality, validate_pure_enrollment_quality
from app.ai.face_engine import detect_faces, align_face, estimate_pose, generate_face_embedding
from app.ai.vector_search import search_similar_face
from app.api.deps import require_roles, get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()


def decode_base64_image(image_base64: str) -> np.ndarray:
    """Decode base64 string to OpenCV BGR numpy array."""
    try:
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        img_bytes = base64.b64decode(image_base64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Decoded image is None")
        return img
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 image data: {str(e)}"
        )


@router.post("/sample", response_model=EnrollmentSampleResponse)
def submit_enrollment_sample(
    req: EnrollmentSampleRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.FACULTY])),
    db: Session = Depends(get_db)
):
    """
    Intelligent multi-pose enrollment pipeline.
    
    1. Decode frame
    2. Assess frame quality & lighting
    3. Detect face & landmarks
    4. Estimate head pose & match against target pose
    5. Check duplicate face (prevents identity collision with other students)
    6. Align face and generate embedding
    7. Store high-quality sample in PostgreSQL + pgvector
    8. Return real-time progress and actionable guidance
    """
    student = db.query(Student).filter(Student.id == req.student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    frame = decode_base64_image(req.image_base64)
    target_pose = (req.target_pose or "frontal").lower()

    # Step 1: Quality assessment
    quality_meta = assess_frame_quality(frame)
    is_low_light, _ = detect_low_light(frame)
    
    processed_frame = frame
    if is_low_light:
        processed_frame, _ = enhance_low_light(frame)

    # Step 2: Face Detection
    detected = detect_faces(processed_frame, apply_low_light_check=False)
    if not detected:
        return EnrollmentSampleResponse(
            accepted=False,
            quality_score=0.0,
            detected_pose="none",
            target_pose=target_pose,
            samples_collected=get_sample_count(student.id, db),
            samples_required=settings.ENROLLMENT_MIN_SAMPLES,
            status="collecting",
            feedback_message="No face detected. Look directly at the camera.",
            lighting_ok=not is_low_light,
            blur_ok=quality_meta["blur_score"] >= settings.BLUR_THRESHOLD,
            size_ok=False,
            pose_ok=False
        )

    if len(detected) > 1:
        return EnrollmentSampleResponse(
            accepted=False,
            quality_score=0.0,
            detected_pose="multiple",
            target_pose=target_pose,
            samples_collected=get_sample_count(student.id, db),
            samples_required=settings.ENROLLMENT_MIN_SAMPLES,
            status="collecting",
            feedback_message="Multiple faces detected. Please ensure only one person is in frame.",
            lighting_ok=not is_low_light,
            blur_ok=quality_meta["blur_score"] >= settings.BLUR_THRESHOLD,
            size_ok=True,
            pose_ok=False
        )

    face_info = detected[0]
    face_crop = face_info["face_crop"]
    landmarks = face_info["landmarks"]

    # Step 3: Pure Biometric Quality Assessment
    pure_val = validate_pure_enrollment_quality(
        frame=processed_frame,
        detected_faces=detected,
        target_pose=target_pose,
        strict_liveness=(target_pose != "any")
    )

    if not pure_val["is_pure"]:
        return EnrollmentSampleResponse(
            accepted=False,
            quality_score=pure_val["purity_score"] / 100.0,
            detected_pose=pure_val["detected_pose"],
            target_pose=target_pose,
            samples_collected=get_sample_count(student.id, db),
            samples_required=settings.ENROLLMENT_MIN_SAMPLES,
            status="collecting",
            feedback_message=pure_val["actionable_feedback"],
            lighting_ok=pure_val["checks"]["lighting"],
            blur_ok=pure_val["checks"]["sharpness"],
            size_ok=pure_val["checks"]["face_size"],
            pose_ok=pure_val["checks"]["pose_match"]
        )

    detected_pose = pure_val["detected_pose"]

    # Step 5: Align face & generate embedding
    aligned_face = align_face(face_crop, landmarks)
    embedding_vec = generate_face_embedding(aligned_face)

    # Step 6: Check for duplicate identity in existing enrolled students
    dup_match = search_similar_face(embedding_vec, db, threshold=0.85)
    if dup_match and dup_match["recognized"] and dup_match["student_id"] != student.id:
        return EnrollmentSampleResponse(
            accepted=False,
            quality_score=pure_val["purity_score"] / 100.0,
            detected_pose=detected_pose,
            target_pose=target_pose,
            samples_collected=get_sample_count(student.id, db),
            samples_required=settings.ENROLLMENT_MIN_SAMPLES,
            status="failed",
            feedback_message=f"Duplicate face detected! Matches existing student {dup_match['student_name']} ({dup_match['student_code']}).",
            lighting_ok=True,
            blur_ok=True,
            size_ok=True,
            pose_ok=True
        )

    # Step 7: Persist high quality face embedding
    face_emb_record = FaceEmbedding(
        student_id=student.id,
        pose=detected_pose,
        quality_score=pure_val["purity_score"] / 100.0,
        is_active=True
    )
    face_emb_record.set_embedding(embedding_vec)
    db.add(face_emb_record)
    db.commit()

    current_count = get_sample_count(student.id, db)
    is_ready = current_count >= settings.ENROLLMENT_MIN_SAMPLES
    status_str = "ready" if is_ready else "collecting"
    
    msg = f"Sample accepted for '{detected_pose}' pose! ({current_count}/{settings.ENROLLMENT_MIN_SAMPLES})"
    if is_ready:
        msg = f"Enrollment complete! {current_count} high-quality samples captured."

    return EnrollmentSampleResponse(
        accepted=True,
        quality_score=pure_val["purity_score"] / 100.0,
        detected_pose=detected_pose,
        target_pose=target_pose,
        samples_collected=current_count,
        samples_required=settings.ENROLLMENT_MIN_SAMPLES,
        status=status_str,
        feedback_message=msg,
        lighting_ok=True,
        blur_ok=True,
        size_ok=True,
        pose_ok=True
    )


def get_sample_count(student_id: int, db: Session) -> int:
    """Helper to get current active embedding count."""
    return db.query(func.count(FaceEmbedding.id)).filter(
        FaceEmbedding.student_id == student_id,
        FaceEmbedding.is_active == True
    ).scalar() or 0


@router.get("/status/{student_id}", response_model=EnrollmentStatusResponse)
def get_enrollment_status(
    student_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current face enrollment progress and quality metrics for a student."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    embeddings = db.query(FaceEmbedding).filter(
        FaceEmbedding.student_id == student.id,
        FaceEmbedding.is_active == True
    ).all()

    count = len(embeddings)
    poses = list(set(e.pose for e in embeddings))
    avg_qual = float(np.mean([e.quality_score for e in embeddings])) if embeddings else 0.0

    return EnrollmentStatusResponse(
        student_id=student.id,
        student_name=student.name,
        is_enrolled=(count >= settings.ENROLLMENT_MIN_SAMPLES),
        sample_count=count,
        samples_required=settings.ENROLLMENT_MIN_SAMPLES,
        average_quality_score=round(avg_qual, 2),
        poses_covered=poses
    )


@router.post("/reset")
def reset_enrollment(
    req: ResetEnrollmentRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.FACULTY])),
    db: Session = Depends(get_db)
):
    """Delete all existing face embeddings for a student to allow fresh re-enrollment."""
    student = db.query(Student).filter(Student.id == req.student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    deleted = db.query(FaceEmbedding).filter(FaceEmbedding.student_id == req.student_id).delete()
    db.commit()
    return {"status": "success", "message": f"Cleared {deleted} face embeddings for {student.name}"}


# In-memory recent submissions feed for real-time dashboard display
RECENT_WEB_SUBMISSIONS: List[dict] = []


@router.get("/students-list")
def get_students_list(db: Session = Depends(get_db)):
    """Public helper for web enrollment portal to list or autocomplete registered students."""
    students = db.query(Student).filter(Student.is_active == True).order_by(Student.student_code).all()
    return [
        {
            "id": s.id,
            "student_code": s.student_code,
            "name": s.name,
            "department": s.department
        }
        for s in students
    ]


@router.get("/recent-submissions")
def get_recent_submissions():
    """Retrieve recent web submissions with registration numbers for dashboard display."""
    return RECENT_WEB_SUBMISSIONS[-30:][::-1]


@router.post("/web-submit", response_model=WebEnrollmentSubmitResponse)
def submit_web_enrollment(
    req: WebEnrollmentSubmitRequest,
    db: Session = Depends(get_db)
):
    """
    Dedicated endpoint for the separate web capture portal.
    Captures photo strictly inside the circle, saves the photo file on disk,
    validates 100% biometric purity, and stores the photo along with the registration number in the database.
    """
    student_code = (req.student_code or "").strip().upper()
    if not student_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student registration number / roll code is required.")

    # 1. Lookup student or auto-create if not yet registered
    student = db.query(Student).filter(Student.student_code == student_code).first()
    if not student:
        student = Student(
            student_code=student_code,
            name=f"Student {student_code}",
            email=f"{student_code.lower()}@college.edu",
            department="Computer Science",
            year=1,
            is_active=True
        )
        db.add(student)
        db.commit()
        db.refresh(student)

    # 2. Decode high-resolution image
    frame = decode_base64_image(req.image_base64)
    target_pose = (req.target_pose or "frontal").lower()

    # 3. Save photo to persistent disk storage
    storage_dir = os.path.join(os.getcwd(), "storage", "enrollments", student_code)
    os.makedirs(storage_dir, exist_ok=True)
    filename = f"{student_code}_{target_pose}_{int(time.time())}.jpg"
    abs_photo_path = os.path.join(storage_dir, filename)
    cv2.imwrite(abs_photo_path, frame)
    rel_photo_path = os.path.join("storage", "enrollments", student_code, filename)

    # 4. Face detection and 100% pure biometric validation
    detected_faces = detect_faces(frame)
    strict_liveness = (target_pose != "any")
    pure_val = validate_pure_enrollment_quality(
        frame=frame,
        detected_faces=detected_faces,
        target_pose=target_pose,
        strict_liveness=strict_liveness
    )

    is_pure = bool(pure_val.get("is_pure", False))
    p_score = float(pure_val.get("purity_score", 0.0))
    feedback = str(pure_val.get("actionable_feedback", ""))
    detected_pose = str(pure_val.get("detected_pose", target_pose))

    submission_entry = {
        "student_code": student_code,
        "student_name": student.name,
        "target_pose": target_pose,
        "purity_score": p_score,
        "is_pure": is_pure,
        "photo_path": rel_photo_path,
        "stored_in_db": False,
        "timestamp": int(time.time()),
        "actionable_feedback": feedback
    }

    if not is_pure:
        RECENT_WEB_SUBMISSIONS.append(submission_entry)
        return WebEnrollmentSubmitResponse(
            status="rejected",
            is_pure=False,
            purity_score=p_score,
            message=feedback,
            student_code=student_code,
            student_name=student.name,
            target_pose=target_pose,
            photo_path=rel_photo_path,
            stored_in_db=False,
            actionable_feedback=feedback
        )

    # 5. Check duplicate face across other students
    face = detected_faces[0]
    aligned = align_face(face["face_crop"], face.get("landmarks"))
    new_vec = generate_face_embedding(aligned)
    dup = search_similar_face(new_vec, db, threshold=0.85)

    if dup and dup["recognized"] and dup["student_id"] != student.id:
        conflict_msg = f"Duplicate identity match with student {dup['student_name']} ({dup['student_code']})."
        submission_entry["actionable_feedback"] = conflict_msg
        RECENT_WEB_SUBMISSIONS.append(submission_entry)
        return WebEnrollmentSubmitResponse(
            status="conflict",
            is_pure=False,
            purity_score=p_score,
            message=conflict_msg,
            student_code=student_code,
            student_name=student.name,
            target_pose=target_pose,
            photo_path=rel_photo_path,
            stored_in_db=False,
            actionable_feedback=conflict_msg
        )

    # 6. Store face embedding with photo_path in database
    new_fe = FaceEmbedding(
        student_id=student.id,
        pose=detected_pose,
        quality_score=p_score,
        photo_path=rel_photo_path,
        is_active=True
    )
    new_fe.set_embedding(new_vec)
    db.add(new_fe)
    db.commit()
    db.refresh(new_fe)

    submission_entry["stored_in_db"] = True
    RECENT_WEB_SUBMISSIONS.append(submission_entry)

    return WebEnrollmentSubmitResponse(
        status="success",
        is_pure=True,
        purity_score=p_score,
        message=f"100% Pure sample stored for Registration Number: {student_code}!",
        student_code=student_code,
        student_name=student.name,
        target_pose=target_pose,
        photo_path=rel_photo_path,
        stored_in_db=True,
        actionable_feedback=feedback
    )

