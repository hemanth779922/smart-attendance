import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = 'Smart Attendance System'
    PROJECT_VERSION: str = '2.0.0'
    API_V1_STR: str = '/api/v1'
    
    ENVIRONMENT: str = 'development'
    DEBUG: bool = True
    
    SECRET_KEY: str = 'supersecret-jwt-key-replace-in-production-09a8f7b6c5d4e3f2'
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    BACKEND_CORS_ORIGINS: List[str] = [
        'http://localhost:3000',
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        '*'
    ]
    
    DATABASE_URL: str = Field(
        default='sqlite:///./smart_attendance.db',
        description='Database connection URL. For PostgreSQL + pgvector use postgresql://user:pass@localhost:5432/attendance_db'
    )
    
    FACE_MATCH_THRESHOLD: float = Field(
        default=0.65,
        description='Cosine similarity threshold for face recognition'
    )
    LOW_LIGHT_THRESHOLD: float = Field(
        default=45.0,
        description='Mean luminance threshold below which low-light enhancement is triggered'
    )
    LOW_LIGHT_HIST_CLIP_PERCENTILE: float = Field(
        default=15.0,
        description='Threshold percentage of dark pixels to trigger low-light enhancement'
    )
    BLUR_THRESHOLD: float = Field(
        default=40.0,
        description='Laplacian variance threshold for blur detection'
    )
    MIN_FACE_SIZE: int = Field(
        default=80,
        description='Minimum bounding box width/height in pixels'
    )
    MAX_FACE_POSE_ANGLE: float = Field(
        default=35.0,
        description='Maximum yaw/pitch/roll angle in degrees'
    )
    MIN_IMAGE_CONTRAST: float = Field(
        default=25.0,
        description='Minimum standard deviation of grayscale frame brightness'
    )
    
    LIVENESS_THRESHOLD: float = Field(
        default=0.60,
        description='Minimum aggregate liveness score required to pass'
    )
    SPOOF_THRESHOLD: float = Field(
        default=0.45,
        description='Maximum allowable spoof score'
    )
    EYE_AR_THRESHOLD: float = Field(
        default=0.22,
        description='Eye Aspect Ratio threshold for blink detection'
    )
    TEXTURE_LBP_THRESHOLD: float = Field(
        default=0.35,
        description='LBP texture variation threshold for print/screen attack detection'
    )
    CHALLENGE_TIMEOUT_SECONDS: int = Field(
        default=15,
        description='Maximum time allowed to complete an anti-spoofing challenge'
    )
    
    ENROLLMENT_MIN_SAMPLES: int = Field(
        default=5,
        description='Number of distinct high-quality face samples required for enrollment'
    )
    ENROLLMENT_MIN_QUALITY_SCORE: float = Field(
        default=0.70,
        description='Minimum combined quality score for a sample'
    )
    
    EMBEDDING_DIM: int = 128
    RATE_LIMIT_PER_MINUTE: int = 120
    AUDIT_LOG_ENABLED: bool = True
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = True


settings = Settings()
