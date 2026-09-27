from typing import Optional, List
from pydantic import BaseModel


class EnrollmentSampleRequest(BaseModel):
    student_id: int
    image_base64: str
    target_pose: Optional[str] = "frontal"  # frontal, left, right, smile


class EnrollmentSampleResponse(BaseModel):
    accepted: bool
    quality_score: float
    detected_pose: str
    target_pose: str
    samples_collected: int
    samples_required: int
    status: str  # collecting, ready, failed
    feedback_message: str
    lighting_ok: bool
    blur_ok: bool
    size_ok: bool
    pose_ok: bool


class EnrollmentStatusResponse(BaseModel):
    student_id: int
    student_name: str
    is_enrolled: bool
    sample_count: int
    samples_required: int
    average_quality_score: float
    poses_covered: List[str]


class ResetEnrollmentRequest(BaseModel):
    student_id: int


class WebEnrollmentSubmitRequest(BaseModel):
    student_code: str
    student_name: Optional[str] = None
    department: Optional[str] = "General"
    target_pose: Optional[str] = "frontal"
    image_base64: str
    auto_store: Optional[bool] = True


class WebEnrollmentSubmitResponse(BaseModel):
    status: str
    is_pure: bool
    purity_score: float
    message: str
    student_code: str
    student_name: str
    target_pose: str
    photo_path: Optional[str] = None
    stored_in_db: bool = False
    actionable_feedback: Optional[str] = None
    csv_stored: bool = True
    excel_stored: bool = True

