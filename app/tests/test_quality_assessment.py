import cv2
import numpy as np
from app.ai.quality_assessment import assess_frame_quality
from app.core.config import settings


def test_quality_assessment_blurred_frame():
    # Blurred frame has very low Laplacian variance
    blurred = np.full((200, 200, 3), 100, dtype=np.uint8)
    blurred = cv2.GaussianBlur(blurred, (25, 25), 0)
    res = assess_frame_quality(blurred)
    assert res["blur_score"] < settings.BLUR_THRESHOLD
    assert res["quality_ok"] is False
    assert "Hold the camera steady" in res["actionable_feedback"] or "contrast" in res["reason"].lower()


def test_quality_assessment_too_dark():
    # Extremely dark frame
    very_dark = np.full((200, 200, 3), 5, dtype=np.uint8)
    res = assess_frame_quality(very_dark)
    assert res["quality_ok"] is False
    assert res["brightness"] < settings.LOW_LIGHT_THRESHOLD
    assert "Move to a brighter area" in res["actionable_feedback"]


def test_quality_assessment_small_face():
    # Small face bounding box below MIN_FACE_SIZE (e.g. 40px < 80px)
    frame = np.random.randint(40, 220, (300, 300, 3), dtype=np.uint8)
    res = assess_frame_quality(frame, face_bbox=(10, 10, 40, 40))
    assert res["face_size"] == 40
    assert res["quality_ok"] is False
    assert "Move closer to the camera" in res["actionable_feedback"]


def test_quality_assessment_good_frame():
    # High contrast, sharp frame with reasonable face size
    good_frame = np.random.randint(60, 200, (300, 300, 3), dtype=np.uint8)
    res = assess_frame_quality(good_frame, face_bbox=(50, 50, 120, 120))
    assert res["face_size"] == 120
    assert res["brightness"] >= settings.LOW_LIGHT_THRESHOLD / 2


def test_validate_pure_enrollment_quality_no_faces():
    from app.ai.quality_assessment import validate_pure_enrollment_quality
    dummy_frame = np.full((300, 300, 3), 128, dtype=np.uint8)
    res = validate_pure_enrollment_quality(dummy_frame, detected_faces=[])
    assert res["is_pure"] is False
    assert res["reason"] == "No face detected in frame"
    assert res["checks"]["face_size"] is False


def test_validate_pure_enrollment_quality_multiple_faces():
    from app.ai.quality_assessment import validate_pure_enrollment_quality
    dummy_frame = np.full((300, 300, 3), 128, dtype=np.uint8)
    face1 = {"face_crop": np.full((100, 100, 3), 128, dtype=np.uint8), "bbox": (10, 10, 100, 100)}
    face2 = {"face_crop": np.full((100, 100, 3), 128, dtype=np.uint8), "bbox": (150, 150, 100, 100)}
    res = validate_pure_enrollment_quality(dummy_frame, detected_faces=[face1, face2])
    assert res["is_pure"] is False
    assert "Multiple people detected" in res["actionable_feedback"]
    assert res["checks"]["single_face"] is False


def test_validate_pure_enrollment_quality_blurred_face():
    from app.ai.quality_assessment import validate_pure_enrollment_quality
    blurred_crop = np.full((120, 120, 3), 128, dtype=np.uint8)
    blurred_crop = cv2.GaussianBlur(blurred_crop, (31, 31), 0)
    face = {
        "face_crop": blurred_crop,
        "bbox": (10, 10, 120, 120),
        "landmarks": {
            "right_eye": (40, 40),
            "left_eye": (80, 40),
            "nose": (60, 60),
            "right_mouth": (45, 90),
            "left_mouth": (75, 90)
        }
    }
    res = validate_pure_enrollment_quality(blurred_crop, detected_faces=[face], target_pose="frontal", strict_liveness=False)
    assert res["is_pure"] is False
    assert res["checks"]["sharpness"] is False
    assert any("blurred" in r.lower() for r in res["reasons"])

