import os
import threading
import cv2
import numpy as np
import urllib.request
import urllib.error
import time
import logging
from typing import Dict, Any, Tuple, Optional
from app.ai.face_engine import detect_faces, estimate_pose
from app.ai.quality_assessment import validate_pure_enrollment_quality

logger = logging.getLogger(__name__)


def normalize_ip_webcam_url(raw_url: str) -> str:
    """Ensure URL has http:// prefix and standard format."""
    url = raw_url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url
    return url.rstrip("/")


def get_snapshot_url(base_url: str) -> str:
    """Derive shot.jpg snapshot endpoint from IP Webcam base or video URL."""
    norm = normalize_ip_webcam_url(base_url)
    if norm.endswith("/video"):
        norm = norm[:-6]
    elif norm.endswith("/shot.jpg"):
        return norm
    return f"{norm}/shot.jpg"


def get_video_stream_url(base_url: str) -> str:
    """Derive /video MJPEG stream URL from IP Webcam base URL."""
    norm = normalize_ip_webcam_url(base_url)
    if norm.endswith("/video"):
        return norm
    elif norm.endswith("/shot.jpg"):
        norm = norm[:-9]
    return f"{norm}/video"


def test_ip_webcam_connection(ip_url: str, timeout_sec: float = 2.0) -> Dict[str, Any]:
    """Test if IP Webcam server is reachable and responsive."""
    norm = normalize_ip_webcam_url(ip_url)
    shot_url = get_snapshot_url(norm)
    try:
        req = urllib.request.Request(
            shot_url,
            headers={"User-Agent": "SmartAttendance/2.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            if resp.status == 200:
                data = resp.read()
                if len(data) > 1000:
                    return {
                        "connected": True,
                        "url": norm,
                        "message": f"Successfully connected to Phone IP Webcam ({round(len(data)/1024, 1)} KB frame received)."
                    }
    except Exception as e:
        logger.debug(f"IP Webcam connection failed for {shot_url}: {e}")
        return {
            "connected": False,
            "url": norm,
            "message": f"Could not connect to {norm}. Make sure 'IP Webcam' app has 'Start server' turned ON on your phone."
        }

    return {
        "connected": False,
        "url": norm,
        "message": f"Could not fetch valid video frame from {norm}."
    }


def fetch_ip_webcam_frame(ip_url: str, timeout_sec: float = 2.5) -> Optional[np.ndarray]:
    """Fetch high-resolution raw frame from Phone IP Webcam."""
    shot_url = get_snapshot_url(ip_url)
    try:
        req = urllib.request.Request(
            shot_url,
            headers={"User-Agent": "SmartAttendance/2.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            if resp.status == 200:
                img_bytes = resp.read()
                nparr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                return frame
    except Exception as e:
        logger.warning(f"Error reading frame from IP Webcam {shot_url}: {e}")
    return None


def check_ring_alignment(frame_shape: Tuple[int, ...], bbox: Tuple[int, int, int, int]) -> Tuple[bool, str, Dict[str, float]]:
    """
    Rigorously check if face bounding box is properly positioned inside the vertical oval ring.
    Oval is defined at center cx=0.50, cy=0.48 with vertical proportion.
    """
    fh, fw = frame_shape[:2]
    bx, by, bw, bh = bbox

    norm_cx = float((bx + bw / 2.0) / fw)
    norm_cy = float((by + bh / 2.0) / fh)
    norm_w = float(bw / fw)
    norm_h = float(bh / fh)

    coords = {
        "norm_cx": round(norm_cx, 3),
        "norm_cy": round(norm_cy, 3),
        "norm_w": round(norm_w, 3),
        "norm_h": round(norm_h, 3)
    }

    # Strict Center Tolerance: [0.38, 0.62] horizontally, [0.30, 0.64] vertically
    if norm_cx < 0.38:
        return False, "FACE TOO FAR LEFT - MOVE RIGHT INTO CIRCLE", coords
    if norm_cx > 0.62:
        return False, "FACE TOO FAR RIGHT - MOVE LEFT INTO CIRCLE", coords
    if norm_cy < 0.30:
        return False, "FACE TOO HIGH - LOWER HEAD INTO CIRCLE", coords
    if norm_cy > 0.64:
        return False, "FACE TOO LOW - RAISE HEAD INTO CIRCLE", coords

    # Strict Size Tolerance: Face must comfortably fill the vertical oval
    if norm_w < 0.17 or norm_h < 0.22:
        return False, "FACE TOO FAR AWAY - MOVE CLOSER TO FILL CIRCLE", coords
    if norm_w > 0.58 or norm_h > 0.70:
        return False, "FACE TOO CLOSE - STEP BACK SLIGHTLY", coords

    return True, "Face centered inside circle", coords


def check_face_clarity(face_crop: np.ndarray) -> Tuple[bool, str, Dict[str, float]]:
    """
    Rigorously check that face region is sharp, crisp, well-focused and well-lit.
    Rejects blurry, motion-degraded, or underexposed/overexposed faces.
    """
    if face_crop is None or face_crop.size == 0:
        return False, "INVALID FACE REGION", {"sharpness": 0.0, "brightness": 0.0}

    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY) if len(face_crop.shape) == 3 else face_crop
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    metrics = {
        "sharpness": round(sharpness, 1),
        "brightness": round(brightness, 1),
        "contrast": round(contrast, 1)
    }

    # Exposure check
    if brightness < 52.0:
        return False, f"FACE TOO DARK (Level: {round(brightness, 1)}). Move closer to light.", metrics
    if brightness > 225.0:
        return False, f"FACE TOO BRIGHT / GLARE (Level: {round(brightness, 1)}). Avoid bright background light.", metrics

    # Sharpness / Focus check (phone cameras are high res, so >= 45 is a clear baseline)
    if sharpness < 42.0:
        return False, f"FACE BLURRY (Score: {round(sharpness, 1)}). Hold phone completely still.", metrics

    # Contrast check
    if contrast < 22.0:
        return False, "FACE LACKS DEFINITION. Adjust lighting.", metrics

    return True, "Face is sharp and clear", metrics


def evaluate_frame_ring_and_purity(
    frame: np.ndarray,
    target_pose: str = "frontal",
    strict_liveness: bool = True
) -> Dict[str, Any]:
    """
    Complete end-to-end evaluation of a camera frame:
    1. Detects face(s).
    2. Enforces EXACTLY ONE person visible.
    3. Enforces that face is STRICTLY inside the vertical circle.
    4. Enforces high optical sharpness & balanced lighting.
    5. Validates 100% biometric purity.
    """
    if frame is None or frame.size == 0:
        return {
            "status": "red",
            "is_pure": False,
            "purity_score": 0.0,
            "guidance_message": "NO CAMERA FEED DETECTED",
            "is_in_ring": False,
            "is_clear": False,
            "faces_count": 0,
            "metrics": {}
        }

    faces = detect_faces(frame)
    faces_count = len(faces)

    if faces_count == 0:
        return {
            "status": "red",
            "is_pure": False,
            "purity_score": 0.0,
            "guidance_message": "KEEP YOUR FACE INSIDE THE CIRCLE",
            "is_in_ring": False,
            "is_clear": False,
            "faces_count": 0,
            "metrics": {}
        }

    if faces_count > 1:
        return {
            "status": "red",
            "is_pure": False,
            "purity_score": 0.0,
            "guidance_message": "MULTIPLE PEOPLE DETECTED! ONLY APPLICANT SHOULD BE IN FRAME",
            "is_in_ring": False,
            "is_clear": False,
            "faces_count": faces_count,
            "metrics": {}
        }

    face = faces[0]
    bbox = face.get("bbox")
    face_crop = face.get("face_crop")

    # 1. Ring Alignment Check
    in_ring, ring_msg, ring_coords = check_ring_alignment(frame.shape, bbox)
    if not in_ring:
        return {
            "status": "red",
            "is_pure": False,
            "purity_score": 25.0,
            "guidance_message": ring_msg,
            "is_in_ring": False,
            "is_clear": False,
            "faces_count": 1,
            "metrics": ring_coords
        }

    # 2. Clarity & Exposure Check
    is_clear, clarity_msg, clarity_metrics = check_face_clarity(face_crop)
    if not is_clear:
        return {
            "status": "red",
            "is_pure": False,
            "purity_score": 48.0,
            "guidance_message": clarity_msg,
            "is_in_ring": True,
            "is_clear": False,
            "faces_count": 1,
            "metrics": {**ring_coords, **clarity_metrics}
        }

    # 3. Comprehensive Pure Biometric Validation
    pure_res = validate_pure_enrollment_quality(
        frame=frame,
        detected_faces=faces,
        target_pose=target_pose,
        strict_liveness=strict_liveness
    )

    is_pure = bool(pure_res.get("is_pure", False))
    purity_score = float(pure_res.get("purity_score", 0.0))

    if is_pure and in_ring and is_clear:
        return {
            "status": "green",
            "is_pure": True,
            "purity_score": 100.0,
            "guidance_message": f"✓ 100% CLEAR IN CIRCLE ({target_pose.upper()} POSE) - READY TO CAPTURE!",
            "is_in_ring": True,
            "is_clear": True,
            "faces_count": 1,
            "metrics": {**ring_coords, **clarity_metrics, "purity_score": 100.0}
        }
    else:
        feedback = pure_res.get("actionable_feedback") or "Keep face steady and clear in circle."
        return {
            "status": "red",
            "is_pure": False,
            "purity_score": min(purity_score, 85.0),
            "guidance_message": feedback,
            "is_in_ring": True,
            "is_clear": False,
            "faces_count": 1,
            "metrics": {**ring_coords, **clarity_metrics, "purity_score": purity_score}
        }


class RealtimeCameraStream:
    """
    Zero-Buffering Real-Time Camera Streamer.
    Continuously drains frames from the camera in a dedicated background thread
    so FFmpeg and socket buffers NEVER build up a backlog of stale frames.
    Always provides the freshest instant frame (latency < 30ms).
    """
    def __init__(self, src):
        self.src = src
        # Force lowest latency and zero socket buffering in FFmpeg
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "fflags;nobuffer|flags;low_delay|max_delay;0"
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.running = False
        self.lock = threading.Lock()
        self.latest_frame = None
        self.frame_count = 0
        self.is_opened = self.cap.isOpened()

        if self.is_opened:
            self.running = True
            self.thread = threading.Thread(target=self._worker, daemon=True)
            self.thread.start()

    def _worker(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue
            with self.lock:
                self.latest_frame = frame
                self.frame_count += 1

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self.lock:
            if self.latest_frame is not None:
                return True, self.latest_frame.copy()
            return False, None

    def release(self):
        self.running = False
        if hasattr(self, "thread") and self.thread.is_alive():
            self.thread.join(timeout=0.4)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
