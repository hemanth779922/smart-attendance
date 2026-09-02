from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class SubjectBase(BaseModel):
    code: str
    name: str
    department: str
    semester: int = 1
    faculty_id: Optional[int] = None
    is_active: bool = True


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    faculty_id: Optional[int] = None
    is_active: Optional[bool] = None


class SubjectResponse(SubjectBase):
    id: int
    created_at: datetime
    faculty_name: Optional[str] = None
    enrolled_student_count: int = 0

    class Config:
        from_attributes = True


class EnrollStudentsRequest(BaseModel):
    student_ids: List[int]
