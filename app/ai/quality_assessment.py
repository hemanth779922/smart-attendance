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
