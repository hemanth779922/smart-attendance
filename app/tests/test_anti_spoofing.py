import numpy as np
from app.ai.anti_spoofing import (
    analyze_texture_lbp,
    analyze_frequency_fourier,
    generate_anti_spoof_challenge,
    verify_anti_spoofing
)


def test_anti_spoof_challenge_generation():
    challenge = generate_anti_spoof_challenge()
    assert "challenge_token" in challenge
    assert challenge["challenge_type"] in ["BLINK", "TURN_LEFT", "TURN_RIGHT", "SMILE"]
    assert "instruction" in challenge
    assert challenge["expires_in_seconds"] > 0


def test_texture_analysis():
    # Natural variable patch vs flat synthetic patch
    natural_patch = np.random.randint(50, 180, (120, 120, 3), dtype=np.uint8)
    flat_patch = np.full((120, 120, 3), 100, dtype=np.uint8)

    nat_score, nat_det = analyze_texture_lbp(natural_patch)
    flat_score, flat_det = analyze_texture_lbp(flat_patch)

    assert "entropy" in nat_det
    assert "entropy" in flat_det
    # Flat patch has low entropy, hence higher spoof probability
    assert flat_score >= nat_score


def test_fourier_frequency_analysis():
    test_patch = np.random.randint(40, 200, (128, 128, 3), dtype=np.uint8)
    score, details = analyze_frequency_fourier(test_patch)
    assert 0.0 <= score <= 1.0
    assert "high_freq_mean" in details


def test_verify_anti_spoofing_composite():
    test_patch = np.random.randint(60, 190, (120, 120, 3), dtype=np.uint8)
    challenge = generate_anti_spoof_challenge()
    
    # Verify with matching challenge
    result = verify_anti_spoofing(
        face_crop=test_patch,
        challenge_token=challenge["challenge_token"],
        detected_action=challenge["challenge_type"]
    )
    assert "is_live" in result
    assert "spoof_score" in result
    assert 0.0 <= result["spoof_score"] <= 1.0
    assert 0.0 <= result["confidence"] <= 1.0
