from fastapi import APIRouter

from app.api.api_v1.auth import router as auth_router
from app.api.api_v1.users import router as users_router
from app.api.api_v1.students import router as students_router
from app.api.api_v1.subjects import router as subjects_router
from app.api.api_v1.enrollment import router as enrollment_router
from app.api.api_v1.attendance import router as attendance_router
from app.api.api_v1.analytics import router as analytics_router
from app.api.api_v1.settings import router as settings_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(students_router, prefix="/students", tags=["Students"])
api_router.include_router(subjects_router, prefix="/subjects", tags=["Subjects"])
api_router.include_router(enrollment_router, prefix="/enrollment", tags=["Intelligent Enrollment"])
api_router.include_router(attendance_router, prefix="/attendance", tags=["Attendance Pipeline"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics & Monitoring"])
api_router.include_router(settings_router, prefix="/settings", tags=["Configuration & Thresholds"])
