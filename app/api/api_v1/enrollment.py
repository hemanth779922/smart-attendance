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
    ResetEnrollmentRequest
)
from app.ai.low_light import detect_low_light, enhance_low_light, assess_face_quality
from app.ai.quality_assessment import assess_frame_quality
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

    # Step 3: Face Quality
    face_quality = assess_face_quality(face_crop)
    if not face_quality["is_usable"]:
        return EnrollmentSampleResponse(
            accepted=False,
            quality_score=face_quality["quality_score"],
            detected_pose="unknown",
            target_pose=target_pose,
            samples_collected=get_sample_count(student.id, db),
            samples_required=settings.ENROLLMENT_MIN_SAMPLES,
            status="collecting",
            feedback_message=quality_meta["actionable_feedback"],
            lighting_ok=not is_low_light,
            blur_ok=face_quality["blur_score"] >= settings.BLUR_THRESHOLD,
            size_ok=min(face_crop.shape[:2]) >= settings.MIN_FACE_SIZE,
            pose_ok=False
        )

    # Step 4: Pose Estimation
    detected_pose, pose_meta = estimate_pose(face_crop, landmarks)
    
    # Check if detected pose matches requested pose or is acceptable
    pose_ok = (target_pose == "any") or (detected_pose == target_pose)
    if not pose_ok:
        pose_guidance = {
            "frontal": "Look straight at the camera",
            "left": "Turn your head slightly to your left",
            "right": "Turn your head slightly to your right",
            "smile": "Smile naturally for the camera"
        }.get(target_pose, f"Adopt {target_pose} pose")

        return EnrollmentSampleResponse(
            accepted=False,
            quality_score=face_quality["quality_score"],
            detected_pose=detected_pose,
            target_pose=target_pose,
            samples_collected=get_sample_count(student.id, db),
            samples_required=settings.ENROLLMENT_MIN_SAMPLES,
            status="collecting",
            feedback_message=f"Detected '{detected_pose}' pose. {pose_guidance}.",
            lighting_ok=True,
            blur_ok=True,
            size_ok=True,
            pose_ok=False
        )

    # Step 5: Align face & generate embedding
    aligned_face = align_face(face_crop, landmarks)
    embedding_vec = generate_face_embedding(aligned_face)

    # Step 6: Check for duplicate identity in existing enrolled students
    dup_match = search_similar_face(embedding_vec, db, threshold=0.85)
    if dup_match and dup_match["recognized"] and dup_match["student_id"] != student.id:
        return EnrollmentSampleResponse(
            accepted=False,
            quality_score=face_quality["quality_score"],
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
        quality_score=face_quality["quality_score"],
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
        quality_score=face_quality["quality_score"],
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
