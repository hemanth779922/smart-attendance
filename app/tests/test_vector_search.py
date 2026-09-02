import numpy as np
from sqlalchemy.orm import Session
from app.ai.vector_search import search_similar_face
from app.ai.face_engine import compute_cosine_similarity
from app.models.student import Student
from app.models.face_embedding import FaceEmbedding
from app.core.config import settings


def test_cosine_similarity_computation():
    v1 = [1.0, 0.0, 0.0] + [0.0] * (settings.EMBEDDING_DIM - 3)
    v2 = [1.0, 0.0, 0.0] + [0.0] * (settings.EMBEDDING_DIM - 3)
    v3 = [0.0, 1.0, 0.0] + [0.0] * (settings.EMBEDDING_DIM - 3)

    assert compute_cosine_similarity(v1, v2) >= 0.999
    assert compute_cosine_similarity(v1, v3) <= 0.001


def test_vector_search_matching(db_session: Session):
    # Create student with embedding
    student = Student(
        student_code="CS101",
        name="John von Neumann",
        email="john@attendance.edu",
        department="Computer Science",
        year=2,
        is_active=True
    )
    db_session.add(student)
    db_session.commit()

    # Generate unit vector embedding
    vec = [0.0] * settings.EMBEDDING_DIM
    vec[0] = 1.0

    fe = FaceEmbedding(
        student_id=student.id,
        pose="frontal",
        quality_score=0.95,
        is_active=True
    )
    fe.set_embedding(vec)
    db_session.add(fe)
    db_session.commit()

    # Search with matching vector
    match = search_similar_face(vec, db_session)
    assert match is not None
    assert match["recognized"] is True
    assert match["student_id"] == student.id
    assert match["similarity"] >= 0.99


def test_vector_search_unknown_face_rejection(db_session: Session):
    student = Student(
        student_code="CS102",
        name="Ada Lovelace",
        email="ada@attendance.edu",
        department="Computer Science",
        year=3,
        is_active=True
    )
    db_session.add(student)
    db_session.commit()

    enrolled_vec = [1.0] + [0.0] * (settings.EMBEDDING_DIM - 1)
    fe = FaceEmbedding(student_id=student.id, pose="frontal", quality_score=0.92, is_active=True)
    fe.set_embedding(enrolled_vec)
    db_session.add(fe)
    db_session.commit()

    # Search with orthogonal / completely different vector
    unrelated_vec = [0.0, 1.0] + [0.0] * (settings.EMBEDDING_DIM - 2)
    match = search_similar_face(unrelated_vec, db_session)
    assert match is not None
    assert match["recognized"] is False
    assert match["similarity"] < settings.FACE_MATCH_THRESHOLD
