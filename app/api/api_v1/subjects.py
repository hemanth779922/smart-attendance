from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.subject import Subject, StudentSubject
from app.models.student import Student
from app.models.user import User, UserRole
from app.schemas.subject import SubjectCreate, SubjectUpdate, SubjectResponse, EnrollStudentsRequest
from app.schemas.student import StudentResponse
from app.api.deps import require_roles, get_current_active_user

router = APIRouter()


@router.get("", response_model=List[SubjectResponse])
def get_subjects(
    skip: int = 0,
    limit: int = 100,
    department: Optional[str] = None,
    faculty_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all subjects with optional department/faculty filters."""
    query = db.query(Subject)
    if department:
        query = query.filter(Subject.department.ilike(f"%{department}%"))
    if faculty_id:
        query = query.filter(Subject.faculty_id == faculty_id)
    elif current_user.role == UserRole.FACULTY:
        # Faculty sees their assigned subjects by default if not admin
        query = query.filter(Subject.faculty_id == current_user.id)

    subjects = query.offset(skip).limit(limit).all()

    results = []
    for sub in subjects:
        enrolled_count = db.query(func.count(StudentSubject.id)).filter(
            StudentSubject.subject_id == sub.id
        ).scalar() or 0
        faculty_name = sub.faculty.full_name if sub.faculty else None
        
        results.append(SubjectResponse(
            id=sub.id,
            code=sub.code,
            name=sub.name,
            department=sub.department,
            semester=sub.semester,
            faculty_id=sub.faculty_id,
            faculty_name=faculty_name,
            is_active=sub.is_active,
            created_at=sub.created_at,
            enrolled_student_count=enrolled_count
        ))

    return results


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(
    subject_in: SubjectCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Create a new subject course (ADMIN only)."""
    existing = db.query(Subject).filter(Subject.code == subject_in.code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject code already exists")

    subject = Subject(
        code=subject_in.code,
        name=subject_in.name,
        department=subject_in.department,
        semester=subject_in.semester,
        faculty_id=subject_in.faculty_id,
        is_active=subject_in.is_active
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)

    faculty_name = subject.faculty.full_name if subject.faculty else None
    return SubjectResponse(
        id=subject.id,
        code=subject.code,
        name=subject.name,
        department=subject.department,
        semester=subject.semester,
        faculty_id=subject.faculty_id,
        faculty_name=faculty_name,
        is_active=subject.is_active,
        created_at=subject.created_at,
        enrolled_student_count=0
    )


@router.get("/{subject_id}", response_model=SubjectResponse)
def get_subject(
    subject_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get subject details by ID."""
    sub = db.query(Subject).filter(Subject.id == subject_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    enrolled_count = db.query(func.count(StudentSubject.id)).filter(
        StudentSubject.subject_id == sub.id
    ).scalar() or 0
    faculty_name = sub.faculty.full_name if sub.faculty else None

    return SubjectResponse(
        id=sub.id,
        code=sub.code,
        name=sub.name,
        department=sub.department,
        semester=sub.semester,
        faculty_id=sub.faculty_id,
        faculty_name=faculty_name,
        is_active=sub.is_active,
        created_at=sub.created_at,
        enrolled_student_count=enrolled_count
    )


@router.put("/{subject_id}", response_model=SubjectResponse)
def update_subject(
    subject_id: int,
    subject_in: SubjectUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.FACULTY])),
    db: Session = Depends(get_db)
):
    """Update subject details."""
    sub = db.query(Subject).filter(Subject.id == subject_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    if subject_in.code is not None and subject_in.code != sub.code:
        if db.query(Subject).filter(Subject.code == subject_in.code).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject code already exists")
        sub.code = subject_in.code

    if subject_in.name is not None:
        sub.name = subject_in.name
    if subject_in.department is not None:
        sub.department = subject_in.department
    if subject_in.semester is not None:
        sub.semester = subject_in.semester
    if subject_in.faculty_id is not None:
        sub.faculty_id = subject_in.faculty_id
    if subject_in.is_active is not None:
        sub.is_active = subject_in.is_active

    db.commit()
    db.refresh(sub)

    enrolled_count = db.query(func.count(StudentSubject.id)).filter(
        StudentSubject.subject_id == sub.id
    ).scalar() or 0
    faculty_name = sub.faculty.full_name if sub.faculty else None

    return SubjectResponse(
        id=sub.id,
        code=sub.code,
        name=sub.name,
        department=sub.department,
        semester=sub.semester,
        faculty_id=sub.faculty_id,
        faculty_name=faculty_name,
        is_active=sub.is_active,
        created_at=sub.created_at,
        enrolled_student_count=enrolled_count
    )


@router.post("/{subject_id}/enroll", status_code=status.HTTP_200_OK)
def enroll_students_to_subject(
    subject_id: int,
    req: EnrollStudentsRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.FACULTY])),
    db: Session = Depends(get_db)
):
    """Enroll a list of students into a subject."""
    sub = db.query(Subject).filter(Subject.id == subject_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    enrolled_count = 0
    for sid in req.student_ids:
        existing = db.query(StudentSubject).filter(
            StudentSubject.subject_id == subject_id,
            StudentSubject.student_id == sid
        ).first()
        if not existing:
            db.add(StudentSubject(subject_id=subject_id, student_id=sid))
            enrolled_count += 1

    db.commit()
    return {"status": "success", "enrolled_count": enrolled_count, "message": f"Enrolled {enrolled_count} students to {sub.name}"}


@router.get("/{subject_id}/students", response_model=List[StudentResponse])
def get_enrolled_students(
    subject_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all students enrolled in a subject."""
    students = db.query(Student).join(
        StudentSubject, Student.id == StudentSubject.student_id
    ).filter(
        StudentSubject.subject_id == subject_id,
        Student.is_active == True
    ).all()

    result = []
    for s in students:
        emb_count = db.query(func.count(FaceEmbedding.id)).filter(
            FaceEmbedding.student_id == s.id,
            FaceEmbedding.is_active == True
        ).scalar() or 0
        result.append(StudentResponse(
            id=s.id,
            student_code=s.student_code,
            name=s.name,
            email=s.email,
            department=s.department,
            year=s.year,
            section=s.section,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at,
            is_enrolled_face=(emb_count >= 1),
            embedding_count=emb_count
        ))
    return result
