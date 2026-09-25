import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.db.base import Base

logger = logging.getLogger(__name__)

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables, extensions, and default seed data."""
    import app.models  # noqa: F401
    from app.models.user import User, UserRole
    from app.models.system_setting import SystemSetting
    from app.core.security import get_password_hash

    if settings.DATABASE_URL.startswith("postgresql"):
        try:
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                logger.info("pgvector extension initialized or already enabled.")
        except Exception as e:
            logger.warning(f"Could not execute CREATE EXTENSION vector: {e}")

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created.")

    if settings.DATABASE_URL.startswith("postgresql"):
        try:
            with engine.connect() as conn:
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_face_embeddings_vector "
                    "ON face_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
                ))
                conn.commit()
                logger.info("pgvector IVFFlat cosine index verified.")
        except Exception as e:
            logger.debug(f"pgvector index creation notice: {e}")

    db = SessionLocal()
    try:
        # Seed default admin
        admin_user = db.query(User).filter(User.email == "admin@attendance.edu").first()
        if not admin_user:
            admin_user = User(
                email="admin@attendance.edu",
                full_name="System Administrator",
                hashed_password=get_password_hash("Admin@12345"),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin_user)
            logger.info("Default ADMIN user seeded: admin@attendance.edu")

        # Seed default faculty
        faculty_user = db.query(User).filter(User.email == "faculty@attendance.edu").first()
        if not faculty_user:
            faculty_user = User(
                email="faculty@attendance.edu",
                full_name="Dr. Alan Turing",
                hashed_password=get_password_hash("Faculty@12345"),
                role=UserRole.FACULTY,
                is_active=True
            )
            db.add(faculty_user)
            logger.info("Default FACULTY user seeded: faculty@attendance.edu")

        # Seed default system settings
        default_settings = {
            "FACE_MATCH_THRESHOLD": str(settings.FACE_MATCH_THRESHOLD),
            "LOW_LIGHT_THRESHOLD": str(settings.LOW_LIGHT_THRESHOLD),
            "BLUR_THRESHOLD": str(settings.BLUR_THRESHOLD),
            "LIVENESS_THRESHOLD": str(settings.LIVENESS_THRESHOLD),
            "SPOOF_THRESHOLD": str(settings.SPOOF_THRESHOLD),
            "ENROLLMENT_MIN_SAMPLES": str(settings.ENROLLMENT_MIN_SAMPLES),
        }
        for k, v in default_settings.items():
            if not db.query(SystemSetting).filter(SystemSetting.key == k).first():
                db.add(SystemSetting(key=k, value=v, description=f"Default threshold for {k}"))

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error during database initialization seed: {e}")
    finally:
        db.close()
