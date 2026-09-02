from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class OverallMetrics(BaseModel):
    total_students: int
    enrolled_students: int
    total_subjects: int
    today_attendance_count: int
    overall_attendance_rate: float
    spoof_rejection_count: int
    low_quality_rejection_count: int


class SubjectAttendanceStat(BaseModel):
    subject_id: int
    subject_code: str
    subject_name: str
    total_enrolled: int
    present_today: int
    attendance_percentage: float


class DailyTrendStat(BaseModel):
    date: str
    present: int
    late: int
    absent: int


class PipelineLatencyMetrics(BaseModel):
    average_preprocessing_ms: float
    average_detection_ms: float
    average_antispoof_ms: float
    average_embedding_ms: float
    average_vector_search_ms: float
    average_total_ms: float
