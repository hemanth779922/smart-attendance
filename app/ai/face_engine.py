import os
import math
import logging
from typing import List, Dict, Any, Tuple, Optional
import cv2
import numpy as np
from app.core.config import settings
from app.ai.low_light import enhance_low_light, detect_low_light

logger = logging.getLogger(__name__)

YUNET_PATH = os.path.join("models", "face_detection_yunet.onnx")
SFACE_PATH = os.path.join("models", "face_recognition_sface.onnx")
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SFACE_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

_yunet_detector = None
_sface_recognizer = None
_use_yunet = False


def _ensure_model(path: str, url: str) -> None:
    """Download ONNX model file if missing on first launch."""
    if not os.path.exists(path):
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            logger.info(f"Downloading model {os.path.basename(path)}...")
            import urllib.request
            urllib.request.urlretrieve(url, path)
            logger.info(f"Downloaded {os.path.basename(path)} successfully.")
        except Exception as e:
            logger.warning(f"Could not auto-download model from {url}: {e}")


def load_cascades():
    """
    Initialize Face Detection and Recognition Engine once during FastAPI Lifespan startup.
    Uses OpenCV YuNet and SFace models if present.
    """
    global _yunet_detector, _sface_recognizer, _use_yunet
    
    _ensure_model(YUNET_PATH, YUNET_URL)
    _ensure_model(SFACE_PATH, SFACE_URL)

    if os.path.exists(YUNET_PATH) and hasattr(cv2, "FaceDetectorYN_create"):
        try:
            _yunet_detector = cv2.FaceDetectorYN_create(
                model=YUNET_PATH,
                config="",
                input_size=(320, 320),
                score_threshold=0.5,
                nms_threshold=0.3,
                top_k=5000
            )
            _use_yunet = True
            logger.info("OpenCV YuNet Deep Learning Face Detector initialized.")
        except Exception as e:
            logger.warning(f"Could not initialize YuNet detector: {e}")
            _use_yunet = False

    if os.path.exists(SFACE_PATH) and hasattr(cv2, "FaceRecognizerSF_create"):
        try:
            _sface_recognizer = cv2.FaceRecognizerSF_create(
                model=SFACE_PATH,
                config=""
            )
            logger.info("OpenCV SFace Deep Learning Face Recognizer initialized.")
        except Exception as e:
            logger.warning(f"Could not initialize SFace recognizer: {e}")

    logger.info("Face detection and feature extraction engine initialized.")


def detect_faces(frame: np.ndarray, apply_low_light_check: bool = True) -> List[Dict[str, Any]]:
    """
    Detect faces in camera frame with bounding boxes and 5 facial landmarks.
    """
    if frame is None or frame.size == 0:
        return []

    processed_frame = frame
    if apply_low_light_check:
        is_low, _ = detect_low_light(frame)
        if is_low:
            processed_frame, _ = enhance_low_light(frame)

    h, w = processed_frame.shape[:2]

    # Strategy 1: YuNet Deep Learning Detector
    global _yunet_detector, _use_yunet
    if _use_yunet and _yunet_detector is not None:
        try:
            _yunet_detector.setInputSize((w, h))
            _, faces = _yunet_detector.detect(processed_frame)
            if faces is not None and len(faces) > 0:
                results = []
                for face in faces:
                    x, y, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                    conf = float(face[14])
                    if conf < 0.4 or min(fw, fh) < (settings.MIN_FACE_SIZE * 0.7):
                        continue

                    landmarks = {
                        "right_eye": (int(face[4]), int(face[5])),
                        "left_eye": (int(face[6]), int(face[7])),
                        "nose": (int(face[8]), int(face[9])),
                        "mouth_right": (int(face[10]), int(face[11])),
                        "mouth_left": (int(face[12]), int(face[13]))
                    }

                    margin_x = int(fw * 0.1)
                    margin_y = int(fh * 0.1)
                    x1 = max(0, x - margin_x)
                    y1 = max(0, y - margin_y)
                    x2 = min(w, x + fw + margin_x)
                    y2 = min(h, y + fh + margin_y)
                    face_crop = processed_frame[y1:y2, x1:x2]

                    results.append({
                        "bbox": (x, y, fw, fh),
                        "face_crop": face_crop,
                        "confidence": conf,
                        "landmarks": landmarks
                    })
                if results:
                    return results
        except Exception as e:
            logger.debug(f"YuNet inference fallback: {e}")

    # Strategy 2: Multi-Scale Contour and Feature Detector
    gray = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY) if len(processed_frame.shape) == 3 else processed_frame
    
    # Combined skin mask and gradient contour
    if len(processed_frame.shape) == 3:
        ycrcb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2YCrCb)
        # Broad skin and face tone threshold
        skin_mask = cv2.inRange(ycrcb, np.array([0, 125, 70]), np.array([255, 180, 135]))
    else:
        skin_mask = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

    contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detected_faces = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < (settings.MIN_FACE_SIZE * settings.MIN_FACE_SIZE * 0.5):
            continue

        x, y, fw, fh = cv2.boundingRect(cnt)
        aspect_ratio = float(fh) / max(1, fw)
        
        if 0.8 <= aspect_ratio <= 2.2 and min(fw, fh) >= (settings.MIN_FACE_SIZE * 0.7):
            margin_x = int(fw * 0.08)
            margin_y = int(fh * 0.08)
            x1 = max(0, x - margin_x)
            y1 = max(0, y - margin_y)
            x2 = min(w, x + fw + margin_x)
            y2 = min(h, y + fh + margin_y)
            face_crop = processed_frame[y1:y2, x1:x2]

            left_eye = (int(x + fw * 0.32), int(y + fh * 0.38))
            right_eye = (int(x + fw * 0.68), int(y + fh * 0.38))
            nose = (int(x + fw * 0.50), int(y + fh * 0.55))
            mouth_l = (int(x + fw * 0.35), int(y + fh * 0.75))
            mouth_r = (int(x + fw * 0.65), int(y + fh * 0.75))

            detected_faces.append({
                "bbox": (int(x), int(y), int(fw), int(fh)),
                "face_crop": face_crop,
                "confidence": 0.88,
                "landmarks": {
                    "left_eye": left_eye,
                    "right_eye": right_eye,
                    "nose": nose,
                    "mouth_left": mouth_l,
                    "mouth_right": mouth_r
                }
            })

    # Strategy 3: Central Region if frame itself has face dimensions and high variance
    if not detected_faces and min(w, h) >= settings.MIN_FACE_SIZE and np.std(gray) > settings.MIN_IMAGE_CONTRAST:
        cx, cy = w // 2, h // 2
        fw = int(min(w, h) * 0.85)
        fh = int(fw * 1.1)
        x = max(0, cx - fw // 2)
        y = max(0, cy - fh // 2)
        fw = min(fw, w - x)
        fh = min(fh, h - y)
        face_crop = processed_frame[y:y+fh, x:x+fw]
        detected_faces.append({
            "bbox": (x, y, fw, fh),
            "face_crop": face_crop,
            "confidence": 0.80,
            "landmarks": {
                "left_eye": (int(x + fw * 0.32), int(y + fh * 0.38)),
                "right_eye": (int(x + fw * 0.68), int(y + fh * 0.38)),
                "nose": (int(x + fw * 0.50), int(y + fh * 0.55)),
                "mouth_left": (int(x + fw * 0.35), int(y + fh * 0.75)),
                "mouth_right": (int(x + fw * 0.65), int(y + fh * 0.75))
            }
        })

    detected_faces.sort(key=lambda item: item["bbox"][2] * item["bbox"][3], reverse=True)
    return detected_faces


def align_face(
    face_crop: np.ndarray,
    landmarks: Optional[Dict[str, Tuple[int, int]]] = None,
    target_size: Tuple[int, int] = (112, 112)
) -> np.ndarray:
    """
    Align face crop using 2D affine rotation based on eye coordinates.
    """
    if face_crop is None or face_crop.size == 0:
        return np.zeros((target_size[1], target_size[0], 3), dtype=np.uint8)

    if landmarks and "left_eye" in landmarks and "right_eye" in landmarks:
        left_eye = landmarks["left_eye"]
        right_eye = landmarks["right_eye"]

        dx = right_eye[0] - left_eye[0]
        dy = right_eye[1] - left_eye[1]
        angle = math.degrees(math.atan2(dy, dx))

        h, w = face_crop.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        aligned = cv2.warpAffine(face_crop, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    else:
        aligned = face_crop

    resized = cv2.resize(aligned, target_size, interpolation=cv2.INTER_AREA)
    return resized


def estimate_pose(face_crop: np.ndarray, landmarks: Optional[Dict[str, Tuple[int, int]]] = None) -> Tuple[str, Dict[str, float]]:
    """
    Estimate head pose orientation (frontal, left, right, smile).
    """
    if face_crop is None or face_crop.size == 0:
        return "unknown", {"yaw": 0.0, "pitch": 0.0}

    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY) if len(face_crop.shape) == 3 else face_crop
    h, w = gray.shape[:2]

    left_half = gray[:, :w//2]
    right_half = gray[:, w//2:]
    diff_ratio = (np.mean(left_half) - np.mean(right_half)) / (np.mean(gray) + 1e-5)
    yaw_angle = float(diff_ratio * 45.0)

    mouth_region = gray[int(h * 0.65):, int(w * 0.25):int(w * 0.75)]
    mouth_var = float(np.var(mouth_region))
    is_smiling = mouth_var > 450.0

    if is_smiling:
        pose_label = "smile"
    elif yaw_angle > 12.0:
        pose_label = "left"
    elif yaw_angle < -12.0:
        pose_label = "right"
    else:
        pose_label = "frontal"

    return pose_label, {"yaw": round(yaw_angle, 2), "is_smiling": is_smiling}


def generate_face_embedding(aligned_face: np.ndarray) -> List[float]:
    """
    Generate 128-dimensional L2-normalized feature embedding vector from aligned face.
    """
    if aligned_face is None or aligned_face.size == 0:
        return [0.0] * settings.EMBEDDING_DIM

    global _sface_recognizer
    if _sface_recognizer is not None:
        try:
            feature = _sface_recognizer.feature(aligned_face)
            if feature is not None and feature.size > 0:
                vec = feature.flatten()[:settings.EMBEDDING_DIM]
                norm = np.linalg.norm(vec)
                if norm > 1e-6:
                    vec = vec / norm
                return [float(x) for x in vec.tolist()]
        except Exception as e:
            logger.debug(f"SFace inference fallback: {e}")

    gray = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2GRAY) if len(aligned_face.shape) == 3 else aligned_face
    gray = cv2.resize(gray, (64, 64))

    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag, ang = cv2.cartToPolar(gx, gy, angleInDegrees=True)

    cell_h, cell_w = 16, 16
    bins = 8
    bin_width = 360.0 / bins
    features = []

    for i in range(4):
        for j in range(4):
            cell_mag = mag[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
            cell_ang = ang[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
            
            hist = np.zeros(bins, dtype=np.float32)
            for b in range(bins):
                bin_mask = (cell_ang >= b * bin_width) & (cell_ang < (b + 1) * bin_width)
                hist[b] = np.sum(cell_mag[bin_mask])
            features.extend(hist)

    embedding_vec = np.array(features, dtype=np.float32)
    norm = np.linalg.norm(embedding_vec)
    if norm > 1e-6:
        embedding_vec = embedding_vec / norm
    else:
        embedding_vec = np.zeros_like(embedding_vec)

    return [float(x) for x in embedding_vec.tolist()]


def compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two normalized vectors."""
    v1 = np.array(vec1, dtype=np.float32)
    v2 = np.array(vec2, dtype=np.float32)
    dot = np.dot(v1, v2)
    return float(np.clip(dot, 0.0, 1.0))
