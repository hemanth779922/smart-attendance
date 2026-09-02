import enum
from datetime import datetime, date, time, timezone
from sqlalchemy import Column, Integer, String, Float, Date, Time, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base


class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    LATE = "LATE"
    ABSENT = "ABSENT"


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    session_date = Column(Date, nullable=False, index=True, default=date.today)
    session_time = Column(Time, nullable=False, default=lambda: datetime.now().time())
    status = Column(Enum(AttendanceStatus), default=AttendanceStatus.PRESENT, nullable=False)
    
    # Verification and Quality Metrics
    confidence = Column(Float, nullable=False, default=1.0)
    spoof_score = Column(Float, nullable=False, default=0.0)
    image_quality_score = Column(Float, nullable=False, default=1.0)
    
    # Verification metadata
    verified_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verification_method = Column(String(50), default="FACE_RECOGNITION", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Database-level unique constraint preventing duplicate attendance per session/date
    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", "session_date", name="uq_student_subject_date"),
    )

    # Relationships
    student = relationship("Student", back_populates="attendance_records")
    subject = relationship("Subject", back_populates="attendance_records")
    verifier = relationship("User", foreign_keys=[verified_by])

    def __repr__(self):
        return f"<Attendance(id={self.id}, student_id={self.student_id}, subject_id={self.subject_id}, date='{self.session_date}', status='{self.status}')>"
