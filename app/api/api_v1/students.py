from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.student import Student
from app.models.face_embedding import FaceEmbedding
from app.models.user import User, UserRole
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse
from app.api.deps import require_roles, get_current_active_user

router = APIRouter()


@router.get("", response_model=List[StudentResponse])
def get_students(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    department: Optional[str] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List students with search and filter parameters (ADMIN, FACULTY, STUDENT)."""
    query = db.query(Student)
    
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (Student.name.ilike(search_fmt)) |
            (Student.student_code.ilike(search_fmt)) |
            (Student.email.ilike(search_fmt))
        )
    if department:
        query = query.filter(Student.department.ilike(f"%{department}%"))
    if year:
        query = query.filter(Student.year == year)

    students = query.offset(skip).limit(limit).all()

    # Enrich with face embedding status
    result = []
    for s in students:
        emb_count = db.query(func.count(FaceEmbedding.id)).filter(
            FaceEmbedding.student_id == s.id,
            FaceEmbedding.is_active == True
        ).scalar() or 0
        
        resp = StudentResponse(
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
        )
        result.append(resp)

    return result


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    student_in: StudentCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.FACULTY])),
    db: Session = Depends(get_db)
):
    """Register a new student record (ADMIN, FACULTY)."""
    existing_code = db.query(Student).filter(Student.student_code == student_in.student_code).first()
    if existing_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A student with this student code/roll number already exists"
        )
    
    existing_email = db.query(Student).filter(Student.email == student_in.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A student with this email address already exists"
        )

    student = Student(
        student_code=student_in.student_code,
        name=student_in.name,
        email=student_in.email,
        department=student_in.department,
        year=student_in.year,
        section=student_in.section,
        is_active=student_in.is_active
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    return StudentResponse(
        id=student.id,
        student_code=student.student_code,
        name=student.name,
        email=student.email,
        department=student.department,
        year=student.year,
        section=student.section,
        is_active=student.is_active,
        created_at=student.created_at,
        updated_at=student.updated_at,
        is_enrolled_face=False,
        embedding_count=0
    )


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get student profile by ID."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    
    emb_count = db.query(func.count(FaceEmbedding.id)).filter(
        FaceEmbedding.student_id == student.id,
        FaceEmbedding.is_active == True
    ).scalar() or 0

    return StudentResponse(
        id=student.id,
        student_code=student.student_code,
        name=student.name,
        email=student.email,
        department=student.department,
        year=student.year,
        section=student.section,
        is_active=student.is_active,
        created_at=student.created_at,
        updated_at=student.updated_at,
        is_enrolled_face=(emb_count >= 1),
        embedding_count=emb_count
    )


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    student_in: StudentUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.FACULTY])),
    db: Session = Depends(get_db)
):
    """Update student record (ADMIN, FACULTY)."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    if student_in.student_code is not None and student_in.student_code != student.student_code:
        if db.query(Student).filter(Student.student_code == student_in.student_code).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student code already taken")
        student.student_code = student_in.student_code

    if student_in.email is not None and student_in.email != student.email:
        if db.query(Student).filter(Student.email == student_in.email).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already taken")
        student.email = student_in.email

    if student_in.name is not None:
        student.name = student_in.name
    if student_in.department is not None:
        student.department = student_in.department
    if student_in.year is not None:
        student.year = student_in.year
    if student_in.section is not None:
        student.section = student_in.section
    if student_in.is_active is not None:
        student.is_active = student_in.is_active

    db.commit()
    db.refresh(student)

    emb_count = db.query(func.count(FaceEmbedding.id)).filter(
        FaceEmbedding.student_id == student.id,
        FaceEmbedding.is_active == True
    ).scalar() or 0

    return StudentResponse(
        id=student.id,
        student_code=student.student_code,
        name=student.name,
        email=student.email,
        department=student.department,
        year=student.year,
        section=student.section,
        is_active=student.is_active,
        created_at=student.created_at,
        updated_at=student.updated_at,
        is_enrolled_face=(emb_count >= 1),
        embedding_count=emb_count
    )


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Delete student record (ADMIN only)."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    db.delete(student)
    db.commit()
    return None
