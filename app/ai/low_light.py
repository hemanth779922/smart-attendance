import logging
from typing import Tuple, Dict, Any, Optional
import cv2
import numpy as np
from app.core.config import settings

logger = logging.getLogger(__name__)


def detect_low_light(frame: np.ndarray) -> Tuple[bool, Dict[str, Any]]:
    """
    Detect whether the input image/frame is poorly illuminated.
    """
    if frame is None or frame.size == 0:
        return False, {"mean_luminance": 0.0, "shadow_percentage": 0.0, "is_low_light": False}

    if len(frame.shape) == 3:
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        y_channel = ycrcb[:, :, 0]
    else:
        y_channel = frame

    mean_luminance = float(np.mean(y_channel))
    std_luminance = float(np.std(y_channel))
    
    shadow_pixels = np.count_nonzero(y_channel < 30)
    total_pixels = y_channel.size
    shadow_percentage = float((shadow_pixels / total_pixels) * 100.0)

    is_low_light = (
        mean_luminance < settings.LOW_LIGHT_THRESHOLD or 
        shadow_percentage > settings.LOW_LIGHT_HIST_CLIP_PERCENTILE
    )

    metrics = {
        "mean_luminance": round(mean_luminance, 2),
        "std_luminance": round(std_luminance, 2),
        "shadow_percentage": round(shadow_percentage, 2),
        "threshold": settings.LOW_LIGHT_THRESHOLD,
        "is_low_light": is_low_light
    }

    return is_low_light, metrics


def enhance_low_light(
    frame: np.ndarray,
    force: bool = False,
    clip_limit: float = 2.5,
    gamma: Optional[float] = None
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Apply modular lightweight image enhancement to low-light frames.
    """
    if frame is None or frame.size == 0:
        return frame, {"enhanced": False, "reason": "empty_frame"}

    is_low_light, metrics = detect_low_light(frame)
    if not is_low_light and not force:
        return frame, {
            "enhanced": False,
            "reason": "sufficient_lighting",
            "metrics_before": metrics
        }

    if len(frame.shape) == 3:
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)
    else:
        y = frame.copy()
        cr, cb = None, None

    mean_y = metrics["mean_luminance"]

    # 1. CLAHE on Luminance
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    y_clahe = clahe.apply(y)

    # 2. Adaptive Gamma Correction (gamma < 1.0 brightens shadows)
    if gamma is None:
        calc_gamma = float(np.clip(0.4 + (mean_y / 100.0) * 0.4, 0.45, 0.85))
    else:
        calc_gamma = gamma

    table = np.array([((i / 255.0) ** calc_gamma) * 255 for i in range(256)]).astype("uint8")
    y_gamma = cv2.LUT(y_clahe, table)

    # 3. Bilateral filter to smooth noise
    y_denoised = cv2.bilateralFilter(y_gamma, d=5, sigmaColor=25, sigmaSpace=25)

    # 4. Reconstruct frame
    if len(frame.shape) == 3:
        enhanced_ycrcb = cv2.merge([y_denoised, cr, cb])
        enhanced_frame = cv2.cvtColor(enhanced_ycrcb, cv2.COLOR_YCrCb2BGR)
    else:
        enhanced_frame = y_denoised

    _, metrics_after = detect_low_light(enhanced_frame)

    metadata = {
        "enhanced": True,
        "method": "adaptive_clahe_gamma_bilateral",
        "applied_gamma": round(calc_gamma, 3),
        "metrics_before": metrics,
        "metrics_after": metrics_after
    }

    return enhanced_frame, metadata


def assess_face_quality(face_img: np.ndarray) -> Dict[str, Any]:
    """
    Assess quality parameters of a detected face crop.
    """
    if face_img is None or face_img.size == 0:
        return {"quality_score": 0.0, "is_usable": False, "reason": "empty_face_crop"}

    if len(face_img.shape) == 3:
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = face_img

    h, w = gray.shape[:2]
    
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast = float(np.std(gray))
    
    half_w = w // 2
    left_mean = float(np.mean(gray[:, :half_w]))
    right_mean = float(np.mean(gray[:, half_w:]))
    lighting_symmetry = 1.0 - (abs(left_mean - right_mean) / (max(left_mean, right_mean) + 1e-5))
    lighting_symmetry = max(0.0, min(1.0, lighting_symmetry))

    norm_sharpness = min(1.0, blur_score / 150.0)
    norm_contrast = min(1.0, contrast / 50.0)
    norm_size = min(1.0, min(h, w) / 100.0)

    quality_score = (norm_sharpness * 0.4) + (norm_contrast * 0.3) + (lighting_symmetry * 0.2) + (norm_size * 0.1)
    quality_score = float(round(quality_score, 3))

    is_usable = (
        blur_score >= settings.BLUR_THRESHOLD and
        min(h, w) >= settings.MIN_FACE_SIZE and
        contrast >= settings.MIN_IMAGE_CONTRAST
    )

    return {
        "quality_score": quality_score,
        "blur_score": round(blur_score, 2),
        "contrast": round(contrast, 2),
        "lighting_symmetry": round(lighting_symmetry, 2),
        "dimensions": (w, h),
        "is_usable": is_usable
    }
