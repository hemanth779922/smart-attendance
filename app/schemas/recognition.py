from typing import Optional, List
from pydantic import BaseModel


class QualityAssessmentResult(BaseModel):
    quality_ok: bool
    brightness: float
    blur_score: float
    contrast_score: float
    face_size: int
    reason: Optional[str] = None
    actionable_feedback: str = "Face clearly positioned"


class AntiSpoofResult(BaseModel):
    is_live: bool
    spoof_score: float
    challenge: str
    confidence: float
    signals: dict = {}
    details: Optional[str] = None


class ChallengeResponse(BaseModel):
    challenge_token: str
    challenge_type: str  # BLINK, TURN_LEFT, TURN_RIGHT, SMILE
    instruction: str
    expires_in_seconds: int


class VerifyChallengeRequest(BaseModel):
    challenge_token: str
    frames_base64: List[str]
