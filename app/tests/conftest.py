import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.subject import Subject, StudentSubject
from app.core.security import get_password_hash, create_access_token

# Test database
TEST_DB_FILE = "./test_attendance.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all test tables at session start and clean up at teardown."""
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass
    
    Base.metadata.create_all(bind=test_engine)
    
    # Seed test users
    db = TestingSessionLocal()
    admin = User(
        email="testadmin@attendance.edu",
        full_name="Test Administrator",
        hashed_password=get_password_hash("Admin@12345"),
        role=UserRole.ADMIN,
        is_active=True
    )
    faculty = User(
        email="testfaculty@attendance.edu",
        full_name="Test Faculty",
        hashed_password=get_password_hash("Faculty@12345"),
        role=UserRole.FACULTY,
        is_active=True
    )
    student_user = User(
        email="teststudent@attendance.edu",
        full_name="Test Student User",
        hashed_password=get_password_hash("Student@12345"),
        role=UserRole.STUDENT,
        is_active=True
    )
    db.add_all([admin, faculty, student_user])
    db.commit()
    db.close()

    yield

    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session for tests."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient with overridden database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token() -> str:
    """JWT token for ADMIN user."""
    return create_access_token(subject="testadmin@attendance.edu", role="ADMIN", user_id=1)


@pytest.fixture
def faculty_token() -> str:
    """JWT token for FACULTY user."""
    return create_access_token(subject="testfaculty@attendance.edu", role="FACULTY", user_id=2)


@pytest.fixture
def student_token() -> str:
    """JWT token for STUDENT user."""
    return create_access_token(subject="teststudent@attendance.edu", role="STUDENT", user_id=3)
