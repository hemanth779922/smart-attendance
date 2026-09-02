from datetime import date, datetime
import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.student import Student
from app.models.subject import Subject
from app.models.attendance import Attendance, AttendanceStatus


def test_database_constraint_prevents_duplicate_attendance(db_session: Session):
    """
    Verify that PostgreSQL / SQLite database unique constraint
    uq_student_subject_date strictly prohibits two records for
    the same (student_id, subject_id, session_date).
    """
    # Create student
    student = Student(
        student_code="CS201",
        name="Grace Hopper",
        email="grace@attendance.edu",
        department="CS",
        year=1,
        is_active=True
    )
    db_session.add(student)

    # Create subject
    subject = Subject(
        code="CS50",
        name="Intro to CS",
        department="CS",
        semester=1,
        is_active=True
    )
    db_session.add(subject)
    db_session.commit()

    today = date.today()
    now_time = datetime.now().time()

    # First attendance insertion succeeds
    att1 = Attendance(
        student_id=student.id,
        subject_id=subject.id,
        session_date=today,
        session_time=now_time,
        status=AttendanceStatus.PRESENT,
        confidence=0.95
    )
    db_session.add(att1)
    db_session.commit()

    # Second attendance insertion with same student + subject + date must fail at DB level!
    att2 = Attendance(
        student_id=student.id,
        subject_id=subject.id,
        session_date=today,
        session_time=now_time,
        status=AttendanceStatus.PRESENT,
        confidence=0.92
    )
    db_session.add(att2)

    with pytest.raises(IntegrityError):
        db_session.commit()
    
    db_session.rollback()
