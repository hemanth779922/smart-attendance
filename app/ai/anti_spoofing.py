import time
import secrets
import logging
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np
from app.core.config import settings

logger = logging.getLogger(__name__)

# Active challenge sessions stored in-memory with expiration
_ACTIVE_CHALLENGES: Dict[str, Dict[str, Any]] = {}


def compute_lbp(gray_image: np.ndarray) -> np.ndarray:
    """Compute Local Binary Pattern (LBP) representation of grayscale image."""
    h, w = gray_image.shape
    lbp = np.zeros((h - 2, w - 2), dtype=np.uint8)
    
    # 8-neighbor comparison
    center = gray_image[1:-1, 1:-1]
    lbp |= ((gray_image[0:-2, 0:-2] >= center) << 7).astype(np.uint8)
    lbp |= ((gray_image[0:-2, 1:-1] >= center) << 6).astype(np.uint8)
    lbp |= ((gray_image[0:-2, 2:] >= center) << 5).astype(np.uint8)
    lbp |= ((gray_image[1:-1, 2:] >= center) << 4).astype(np.uint8)
    lbp |= ((gray_image[2:, 2:] >= center) << 3).astype(np.uint8)
    lbp |= ((gray_image[2:, 1:-1] >= center) << 2).astype(np.uint8)
    lbp |= ((gray_image[2:, 0:-2] >= center) << 1).astype(np.uint8)
    lbp |= ((gray_image[1:-1, 0:-2] >= center) << 0).astype(np.uint8)
    
    return lbp


def analyze_texture_lbp(face_crop: np.ndarray) -> Tuple[float, Dict[str, Any]]:
    """
    Analyze micro-texture using LBP histogram distribution.
    Real skin has rich, smooth micro-texture distributions.
    Printed photos and LCD/OLED screens display flattened, peaked, or unnatural texture histograms.
    
    Returns:
        (spoof_texture_score: float [0.0 to 1.0], details: dict)
    """
    if face_crop is None or face_crop.size == 0:
        return 1.0, {"error": "empty_face"}

    if len(face_crop.shape) == 3:
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = face_crop

    # Resize to standard patch
    resized = cv2.resize(gray, (120, 120))
    lbp = compute_lbp(resized)
    
    # Compute normalized histogram of LBP
    hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256), density=True)
    
    # Entropy / dispersion of the LBP histogram
    non_zero_hist = hist[hist > 1e-6]
    entropy = -np.sum(non_zero_hist * np.log2(non_zero_hist))
    
    # Skin micro-texture typically exhibits high entropy (~5.5 to 7.2)
    # Screens or low-quality prints exhibit lower entropy or artificial spikes
    if entropy < 4.2:
        spoof_score = 0.85
    elif entropy < 5.0:
        spoof_score = 0.55
    elif entropy > 7.5:
        spoof_score = 0.40
    else:
        spoof_score = float(np.clip(1.0 - (entropy - 4.5) / 2.5, 0.05, 0.35))

    return round(spoof_score, 3), {
        "entropy": round(float(entropy), 3),
        "texture_lbp_spoof_prob": spoof_score
    }


def analyze_frequency_fourier(face_crop: np.ndarray) -> Tuple[float, Dict[str, Any]]:
    """
    Detect moiré patterns and screen refresh artifacts via 2D Fast Fourier Transform (FFT).
    Digital displays produce periodic high-frequency harmonic peaks.
    """
    if face_crop is None or face_crop.size == 0:
        return 1.0, {"error": "empty_face"}

    if len(face_crop.shape) == 3:
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = face_crop

    resized = cv2.resize(gray, (128, 128))
    f = np.fft.fft2(resized)
    fshift = np.fft.fftshift(f)
    magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1e-5)

    # Analyze high frequency ring
    rows, cols = resized.shape
    crow, ccol = rows // 2, cols // 2
    
    # Mask out DC center component
    mask = np.ones((rows, cols), np.uint8)
    r_inner = 15
    y, x = np.ogrid[:rows, :cols]
    mask_area = (x - ccol) ** 2 + (y - crow) ** 2 <= r_inner ** 2
    mask[mask_area] = 0
    
    high_freq_mag = magnitude_spectrum * mask
    hf_mean = float(np.mean(high_freq_mag))
    hf_std = float(np.std(high_freq_mag))
    
    # Check for intense periodic moiré spikes
    hf_peak_ratio = float(np.max(high_freq_mag) / (hf_mean + 1e-5))

    if hf_peak_ratio > 3.8:
        freq_spoof_score = 0.75  # Likely screen moiré pattern
    elif hf_peak_ratio > 3.0:
        freq_spoof_score = 0.45
    else:
        freq_spoof_score = 0.10

    return round(freq_spoof_score, 3), {
        "high_freq_mean": round(hf_mean, 2),
        "hf_peak_ratio": round(hf_peak_ratio, 2),
        "freq_spoof_prob": freq_spoof_score
    }


def generate_anti_spoof_challenge() -> Dict[str, Any]:
    """
    Generate a randomized interactive liveness challenge with expiration token.
    Challenges: BLINK, TURN_LEFT, TURN_RIGHT, SMILE
    """
    challenges = [
        ("BLINK", "Please blink your eyes naturally"),
        ("TURN_LEFT", "Please turn your head slightly to your left"),
        ("TURN_RIGHT", "Please turn your head slightly to your right"),
        ("SMILE", "Please smile for the camera")
    ]
    
    choice, instruction = secrets.choice(challenges)
    token = secrets.token_urlsafe(24)
    expires_at = time.time() + settings.CHALLENGE_TIMEOUT_SECONDS

    _ACTIVE_CHALLENGES[token] = {
        "challenge": choice,
        "instruction": instruction,
        "expires_at": expires_at,
        "created_at": time.time()
    }

    # Clean up expired challenges
    now = time.time()
    for k in list(_ACTIVE_CHALLENGES.keys()):
        if _ACTIVE_CHALLENGES[k]["expires_at"] < now:
            _ACTIVE_CHALLENGES.pop(k, None)

    return {
        "challenge_token": token,
        "challenge_type": choice,
        "instruction": instruction,
        "expires_in_seconds": settings.CHALLENGE_TIMEOUT_SECONDS
    }


def verify_anti_spoofing(
    face_crop: np.ndarray,
    temporal_frames: Optional[List[np.ndarray]] = None,
    challenge_token: Optional[str] = None,
    detected_action: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute multi-signal anti-spoofing evaluation.
    
    Combines:
    1. Texture analysis (LBP micro-texture entropy)
    2. Frequency analysis (FFT moiré / display harmonics)
    3. Challenge-Response verification (if challenge token supplied)
    4. Temporal variance analysis (across frame sequence)
    
    Returns:
    {
        "is_live": bool,
        "spoof_score": float,
        "challenge": str,
        "confidence": float,
        "signals": dict,
        "details": str
    }
    """
    if face_crop is None or face_crop.size == 0:
        return {
            "is_live": False,
            "spoof_score": 1.0,
            "challenge": "NONE",
            "confidence": 0.0,
            "signals": {},
            "details": "No face provided for anti-spoofing verification"
        }

    # Signal 1: Texture analysis
    texture_spoof_score, texture_details = analyze_texture_lbp(face_crop)

    # Signal 2: Frequency / Moiré analysis
    freq_spoof_score, freq_details = analyze_frequency_fourier(face_crop)

    # Signal 3: Temporal Motion Consistency
    temporal_spoof_score = 0.15
    temporal_details = {"motion_detected": True}
    if temporal_frames and len(temporal_frames) >= 2:
        diffs = []
        for i in range(len(temporal_frames) - 1):
            f1 = cv2.cvtColor(temporal_frames[i], cv2.COLOR_BGR2GRAY) if len(temporal_frames[i].shape) == 3 else temporal_frames[i]
            f2 = cv2.cvtColor(temporal_frames[i+1], cv2.COLOR_BGR2GRAY) if len(temporal_frames[i+1].shape) == 3 else temporal_frames[i+1]
            diff = np.mean(cv2.absdiff(f1, f2))
            diffs.append(diff)
        avg_motion = float(np.mean(diffs))
        if avg_motion < 0.3:  # Perfectly static frames indicate photo replay or frozen feed
            temporal_spoof_score = 0.80
            temporal_details["motion_detected"] = False
        else:
            temporal_spoof_score = 0.10
            temporal_details["motion_detected"] = True
        temporal_details["avg_motion"] = round(avg_motion, 2)

    # Signal 4: Challenge-Response Check
    challenge_passed = True
    active_challenge_name = "PASSIVE"
    if challenge_token:
        challenge_data = _ACTIVE_CHALLENGES.get(challenge_token)
        if challenge_data:
            if time.time() > challenge_data["expires_at"]:
                challenge_passed = False
                active_challenge_name = challenge_data["challenge"] + "_EXPIRED"
            else:
                active_challenge_name = challenge_data["challenge"]
                if detected_action and detected_action.upper() != active_challenge_name.upper():
                    challenge_passed = False
            # Consume single-use challenge token
            _ACTIVE_CHALLENGES.pop(challenge_token, None)
        else:
            challenge_passed = False
            active_challenge_name = "INVALID_TOKEN"

    # Weighted composite spoof probability
    composite_spoof_score = (texture_spoof_score * 0.45) + (freq_spoof_score * 0.35) + (temporal_spoof_score * 0.20)
    
    if not challenge_passed:
        composite_spoof_score = max(composite_spoof_score, 0.75)

    composite_spoof_score = round(float(composite_spoof_score), 3)
    is_live = (composite_spoof_score < settings.SPOOF_THRESHOLD) and challenge_passed
    confidence = round(float(1.0 - composite_spoof_score), 3)

    return {
        "is_live": is_live,
        "spoof_score": composite_spoof_score,
        "challenge": active_challenge_name,
        "confidence": confidence,
        "signals": {
            "texture": texture_details,
            "frequency": freq_details,
            "temporal": temporal_details,
            "challenge_passed": challenge_passed
        },
        "details": "Multi-signal anti-spoofing check completed"
    }
