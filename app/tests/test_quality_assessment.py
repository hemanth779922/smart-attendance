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
