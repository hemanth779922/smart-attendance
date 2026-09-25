import logging
from typing import Dict, Any, Optional, Tuple
import cv2
import numpy as np
from app.core.config import settings

logger = logging.getLogger(__name__)


def assess_frame_quality(
    frame: np.ndarray,
    face_bbox: Optional[Tuple[int, int, int, int]] = None
) -> Dict[str, Any]:
    """
    Evaluate camera frame quality before recognition or enrollment.
    
    Measures:
    - Brightness (mean luminance)
    - Blur (Laplacian variance)
    - Contrast (Standard deviation)
    - Resolution (Frame dimensions)
    - Face Size (pixels)
    
    Returns:
    {
        "quality_ok": bool,
        "brightness": float,
        "blur_score": float,
        "contrast_score": float,
        "face_size": int,
        "reason": Optional[str],
        "actionable_feedback": str
    }
    """
    if frame is None or frame.size == 0:
        return {
            "quality_ok": False,
            "brightness": 0.0,
            "blur_score": 0.0,
            "contrast_score": 0.0,
            "face_size": 0,
            "reason": "Empty frame received",
            "actionable_feedback": "Camera feed not available"
        }

    h, w = frame.shape[:2]

    # Convert to grayscale for metric extraction
    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame

    # 1. Brightness
    brightness = float(np.mean(gray))

    # 2. Sharpness / Blur score
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # 3. Contrast
    contrast_score = float(np.std(gray))

    # 4. Face Size check
    face_size = 0
    if face_bbox is not None:
        fx, fy, fw, fh = face_bbox
        face_size = min(fw, fh)
    else:
        face_size = min(w, h)

    # 5. Evaluate checks & assign actionable guidance
    quality_ok = True
    reason = None
    feedback = "Face clearly positioned"

    if brightness < settings.LOW_LIGHT_THRESHOLD / 2:
        quality_ok = False
        reason = "Image too dark"
        feedback = "Move to a brighter area"
    elif brightness > 230:
        quality_ok = False
        reason = "Image overexposed / too bright"
        feedback = "Avoid direct bright light behind or on camera"
    elif blur_score < settings.BLUR_THRESHOLD:
        quality_ok = False
        reason = "Image is blurred"
        feedback = "Hold the camera steady"
    elif contrast_score < settings.MIN_IMAGE_CONTRAST:
        quality_ok = False
        reason = "Low image contrast"
        feedback = "Face not clear - adjust lighting"
    elif face_bbox is not None and face_size < settings.MIN_FACE_SIZE:
        quality_ok = False
        reason = f"Face too small ({face_size}px < {settings.MIN_FACE_SIZE}px)"
        feedback = "Move closer to the camera"

    return {
        "quality_ok": quality_ok,
        "brightness": round(brightness, 2),
        "blur_score": round(blur_score, 2),
        "contrast_score": round(contrast_score, 2),
        "face_size": int(face_size),
        "resolution": (w, h),
        "reason": reason,
        "actionable_feedback": feedback
    }


def validate_pure_enrollment_quality(
    frame: np.ndarray,
    detected_faces: list,
    target_pose: str = "frontal",
    strict_liveness: bool = True
) -> Dict[str, Any]:
    """
    Rigorously validate that a face capture meets 100% pure biometric enrollment standards.
    Rejects:
    - Multiple faces or background people
    - Blurry or motion-degraded captures
    - Sub-optimal lighting or harsh directional shadows
    - Low-resolution / far-away faces
    - Spoof attacks (screens / paper printouts)
    - Incorrect head yaw / pitch relative to target pose
    """
    if not detected_faces:
        return {
            "is_pure": False,
            "purity_score": 0.0,
            "grade": "NO_FACE",
            "reason": "No face detected in frame",
            "actionable_feedback": "Please position your face squarely in front of the camera.",
            "checks": {
                "single_face": False,
                "face_size": False,
                "sharpness": False,
                "lighting": False,
                "symmetry": False,
                "landmarks": False,
                "liveness": False,
                "pose_match": False
            },
            "metrics": {}
        }

    if len(detected_faces) > 1:
        return {
            "is_pure": False,
            "purity_score": 0.0,
            "grade": "MULTIPLE_FACES",
            "reason": "Multiple faces detected",
            "actionable_feedback": "Multiple people detected! Ensure ONLY the student is visible in the camera frame.",
            "checks": {
                "single_face": False,
                "face_size": True,
                "sharpness": True,
                "lighting": True,
                "symmetry": True,
                "landmarks": True,
                "liveness": True,
                "pose_match": False
            },
            "metrics": {"face_count": len(detected_faces)}
        }

    face = detected_faces[0]
    face_crop = face["face_crop"]
    landmarks = face.get("landmarks")
    bx, by, bw, bh = face.get("bbox", (0, 0, face_crop.shape[1], face_crop.shape[0]))
    h, w = face_crop.shape[:2]

    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY) if len(face_crop.shape) == 3 else face_crop
    reasons = []

    # 1. Face size check
    min_dim = min(w, h)
    size_ok = min_dim >= 75
    if not size_ok:
        reasons.append(f"Face is too small ({min_dim}px). Step closer to the camera.")

    # 2. Sharpness / Blur check
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    blur_ok = blur_score >= 38.0
    if not blur_ok:
        reasons.append(f"Image is blurred (score: {round(blur_score, 1)}). Hold completely still for high clarity.")

    # 3. Brightness check
    brightness = float(np.mean(gray))
    brightness_ok = (45.0 <= brightness <= 230.0)
    if not brightness_ok:
        reasons.append(f"Lighting is {'too dim' if brightness < 45 else 'too harsh/washed out'} (level: {round(brightness, 1)}).")

    # 4. Contrast check
    contrast = float(np.std(gray))
    contrast_ok = contrast >= 22.0
    if not contrast_ok:
        reasons.append("Low contrast. Face lacks definition.")

    # 5. Lighting symmetry (avoid half-shadowed faces)
    half_w = max(1, w // 2)
    left_mean = float(np.mean(gray[:, :half_w]))
    right_mean = float(np.mean(gray[:, half_w:]))
    symmetry = 1.0 - (abs(left_mean - right_mean) / (max(left_mean, right_mean) + 1e-5))
    symmetry_ok = symmetry >= 0.45
    if not symmetry_ok:
        reasons.append("Uneven lighting. One side of face is in deep shadow.")

    # 6. Landmarks check
    landmarks_ok = (landmarks is not None and len(landmarks) >= 3)
    if landmarks and "right_eye" in landmarks and "left_eye" in landmarks:
        eye_dist = np.hypot(landmarks["left_eye"][0] - landmarks["right_eye"][0], landmarks["left_eye"][1] - landmarks["right_eye"][1])
        landmarks_ok = landmarks_ok and (eye_dist >= 20.0)
    if not landmarks_ok:
        reasons.append("Key facial landmarks not fully visible. Remove sunglasses or obstructions.")

    # 7. Liveness & Anti-Spoofing check
    liveness_ok = True
    spoof_score = 0.1
    if strict_liveness:
        try:
            from app.ai.anti_spoofing import verify_anti_spoofing
            spoof_res = verify_anti_spoofing(face_crop=face_crop)
            spoof_score = spoof_res.get("spoof_score", 0.0)
            liveness_ok = spoof_res.get("is_live", True) and (spoof_score <= settings.SPOOF_THRESHOLD)
            if not liveness_ok:
                reasons.append("Liveness check failed. Printed photos and phone screens are forbidden during enrollment.")
        except Exception as e:
            logger.warning(f"Liveness check exception in enrollment: {e}")

    # 8. Pose compliance check
    from app.ai.face_engine import estimate_pose
    detected_pose, pose_meta = estimate_pose(face_crop, landmarks)
    yaw = pose_meta.get("yaw", 0.0)

    pose_ok = True
    target_pose_clean = (target_pose or "frontal").lower()
    if target_pose_clean == "frontal":
        if abs(yaw) > 16.0:
            pose_ok = False
            reasons.append(f"Face is angled ({round(yaw, 1)}°). Look directly straight into the camera.")
    elif target_pose_clean == "left":
        if yaw < 8.0:
            pose_ok = False
            reasons.append("Turn your head slightly to your left.")
    elif target_pose_clean == "right":
        if yaw > -8.0:
            pose_ok = False
            reasons.append("Turn your head slightly to your right.")
    elif target_pose_clean == "smile":
        if not pose_meta.get("is_smiling", False):
            pose_ok = False
            reasons.append("Please smile naturally for the smile pose sample.")

    # Calculate overall biometric purity percentage
    norm_blur = min(1.0, blur_score / 150.0)
    norm_light = max(0.0, 1.0 - abs(brightness - 128.0) / 115.0)
    norm_contrast = min(1.0, contrast / 50.0)
    norm_sym = max(0.0, min(1.0, symmetry))
    norm_size = min(1.0, min(w, h) / 140.0)
    norm_live = 1.0 - spoof_score

    purity_score = (
        norm_blur * 0.30 +
        norm_light * 0.20 +
        norm_sym * 0.15 +
        norm_contrast * 0.15 +
        norm_size * 0.10 +
        norm_live * 0.10
    ) * 100.0
    purity_score = round(float(purity_score), 1)

    all_checks_passed = (
        size_ok and blur_ok and brightness_ok and contrast_ok and
        symmetry_ok and landmarks_ok and liveness_ok and pose_ok
    )
    is_pure = bool(all_checks_passed and (purity_score >= 68.0))

    if is_pure:
        grade = "100% PURE BIOMETRIC QUALITY"
        feedback = f"✓ Perfect 100% Pure Sample! Purity Score: {purity_score}% ({detected_pose.upper()} pose verified)."
    else:
        grade = "SUB-OPTIMAL (REJECTED)"
        feedback = " | ".join(reasons) if reasons else "Quality did not meet 100% pure biometric standard."

    return {
        "is_pure": bool(is_pure),
        "purity_score": float(purity_score),
        "grade": str(grade),
        "detected_pose": str(detected_pose),
        "target_pose": str(target_pose_clean),
        "actionable_feedback": str(feedback),
        "reasons": [str(r) for r in reasons],
        "checks": {
            "single_face": True,
            "face_size": bool(size_ok),
            "sharpness": bool(blur_ok),
            "lighting": bool(brightness_ok),
            "symmetry": bool(symmetry_ok),
            "landmarks": bool(landmarks_ok),
            "liveness": bool(liveness_ok),
            "pose_match": bool(pose_ok)
        },
        "metrics": {
            "face_width": int(w),
            "face_height": int(h),
            "blur_score": round(float(blur_score), 2),
            "brightness": round(float(brightness), 2),
            "contrast": round(float(contrast), 2),
            "lighting_symmetry": round(float(symmetry), 2),
            "yaw_angle": round(float(yaw), 2),
            "spoof_score": round(float(spoof_score), 2)
        }
    }

