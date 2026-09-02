import enum
from datetime import datetime, date, time
from typing import Optional, List
from pydantic import BaseModel
from app.models.attendance import AttendanceStatus


class VerificationStatus(str, enum.Enum):
    ATTENDANCE_MARKED = "ATTENDANCE_MARKED"
    ALREADY_MARKED = "ALREADY_MARKED"
    UNKNOWN_FACE = "UNKNOWN_FACE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    SPOOF_DETECTED = "SPOOF_DETECTED"
    POOR_IMAGE_QUALITY = "POOR_IMAGE_QUALITY"
    FACE_NOT_DETECTED = "FACE_NOT_DETECTED"
    STUDENT_NOT_ENROLLED_IN_SUBJECT = "STUDENT_NOT_ENROLLED_IN_SUBJECT"


class AttendanceBase(BaseModel):
    student_id: int
    subject_id: int
    session_date: date
    status: AttendanceStatus = AttendanceStatus.PRESENT


class AttendanceCreate(AttendanceBase):
    confidence: float = 1.0
    spoof_score: float = 0.0
    image_quality_score: float = 1.0


class AttendanceResponse(AttendanceBase):
    id: int
    session_time: time
    confidence: float
    spoof_score: float
    image_quality_score: float
    verification_method: str
    created_at: datetime
    student_name: Optional[str] = None
    student_code: Optional[str] = None
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None

    class Config:
        from_attributes = True


class AttendanceVerificationResult(BaseModel):
    status: VerificationStatus
    message: str
    student_id: Optional[int] = None
    student_name: Optional[str] = None
    student_code: Optional[str] = None
    similarity: float = 0.0
    confidence: float = 0.0
    spoof_score: float = 0.0
    quality_score: float = 0.0
    is_live: bool = True
    challenge_passed: bool = True
    attendance_record: Optional[AttendanceResponse] = None
    pipeline_latency_ms: Optional[dict] = None


class MarkAttendanceRequest(BaseModel):
    subject_id: int
    image_base64: str
    challenge_token: Optional[str] = None
    challenge_action: Optional[str] = None
