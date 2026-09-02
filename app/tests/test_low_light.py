import numpy as np
from app.ai.low_light import detect_low_light, enhance_low_light, assess_face_quality
from app.core.config import settings


def test_detect_low_light_on_dark_image():
    # Construct synthetic dark image (mean luminance ~ 15)
    dark_frame = np.full((120, 120, 3), 15, dtype=np.uint8)
    is_low, metrics = detect_low_light(dark_frame)
    assert is_low is True
    assert metrics["mean_luminance"] < settings.LOW_LIGHT_THRESHOLD
    assert metrics["is_low_light"] is True


def test_detect_low_light_on_normal_image():
    # Construct well-lit image (mean luminance ~ 140)
    normal_frame = np.full((120, 120, 3), 140, dtype=np.uint8)
    is_low, metrics = detect_low_light(normal_frame)
    assert is_low is False
    assert metrics["mean_luminance"] >= settings.LOW_LIGHT_THRESHOLD


def test_enhance_low_light_only_when_needed():
    # When lighting is normal, enhancement does not alter frame if force=False
    normal_frame = np.full((100, 100, 3), 130, dtype=np.uint8)
    enhanced, meta = enhance_low_light(normal_frame, force=False)
    assert meta["enhanced"] is False
    np.testing.assert_array_equal(enhanced, normal_frame)


def test_enhance_low_light_improves_dark_image():
    # Dark frame should be enhanced significantly
    dark_frame = np.full((100, 100, 3), 20, dtype=np.uint8)
    enhanced, meta = enhance_low_light(dark_frame)
    assert meta["enhanced"] is True
    assert meta["metrics_after"]["mean_luminance"] > meta["metrics_before"]["mean_luminance"]
    assert np.mean(enhanced) > np.mean(dark_frame)


def test_assess_face_quality_empty_and_normal():
    # Empty face check
    empty_res = assess_face_quality(np.array([]))
    assert empty_res["is_usable"] is False

    # Normal face crop check
    crop = np.random.randint(50, 200, (90, 90, 3), dtype=np.uint8)
    res = assess_face_quality(crop)
    assert "quality_score" in res
    assert "blur_score" in res
    assert 0.0 <= res["quality_score"] <= 1.0
