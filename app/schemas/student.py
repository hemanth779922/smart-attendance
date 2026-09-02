from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class StudentBase(BaseModel):
    student_code: str
    name: str
    email: EmailStr
    department: str
    year: int = 1
    section: Optional[str] = None
    is_active: bool = True


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    student_code: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    year: Optional[int] = None
    section: Optional[str] = None
    is_active: Optional[bool] = None


class StudentResponse(StudentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_enrolled_face: bool = False
    embedding_count: int = 0

    class Config:
        from_attributes = True
