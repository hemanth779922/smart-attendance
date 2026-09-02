import logging
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.models.face_embedding import FaceEmbedding
from app.models.student import Student

logger = logging.getLogger(__name__)


def search_similar_face(
    query_embedding: List[float],
    db: Session,
    threshold: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Search database for the nearest face embedding match using vector similarity.
    
    Supports:
    - PostgreSQL pgvector native `<=>` cosine distance search
    - Vectorized NumPy matrix fallback for SQLite / testing environments
    
    Returns:
    {
        "student_id": int,
        "student_name": str,
        "student_code": str,
        "similarity": float,
        "confidence": float,
        "recognized": bool,
        "pose": str
    }
    """
    if not query_embedding or len(query_embedding) != settings.EMBEDDING_DIM:
        return None

    match_threshold = threshold if threshold is not None else settings.FACE_MATCH_THRESHOLD
    query_vec = np.array(query_embedding, dtype=np.float32)
    
    # Normalize query vector
    q_norm = np.linalg.norm(query_vec)
    if q_norm > 1e-6:
        query_vec = query_vec / q_norm

    # Check if PostgreSQL pgvector query can be used
    if settings.DATABASE_URL.startswith("postgresql"):
        try:
            sql = text("""
                SELECT fe.id, fe.student_id, fe.pose, fe.quality_score,
                       s.name, s.student_code, s.is_active,
                       1 - (fe.embedding <=> :query_vec) as similarity
                FROM face_embeddings fe
                JOIN students s ON fe.student_id = s.id
                WHERE fe.is_active = true AND s.is_active = true
                ORDER BY fe.embedding <=> :query_vec
                LIMIT 1;
            """)
            result = db.execute(sql, {"query_vec": str(query_vec.tolist())}).fetchone()
            if result:
                sim = float(result.similarity)
                is_recognized = sim >= match_threshold
                return {
                    "student_id": result.student_id,
                    "student_name": result.name,
                    "student_code": result.student_code,
                    "similarity": round(sim, 3),
                    "confidence": round(sim, 3),
                    "recognized": is_recognized,
                    "pose": result.pose
                }
        except Exception as e:
            logger.debug(f"Falling back to vectorized search: {e}")

    # Fallback / SQLite high-performance vectorized matrix search
    embeddings = db.query(FaceEmbedding, Student).join(
        Student, FaceEmbedding.student_id == Student.id
    ).filter(
        FaceEmbedding.is_active == True,
        Student.is_active == True
    ).all()

    if not embeddings:
        return {
            "student_id": None,
            "student_name": None,
            "student_code": None,
            "similarity": 0.0,
            "confidence": 0.0,
            "recognized": False,
            "pose": "none"
        }

    matrix = []
    metadata_list = []

    for fe, student in embeddings:
        vec = fe.get_embedding()
        matrix.append(vec)
        metadata_list.append((fe.student_id, student.name, student.student_code, fe.pose))

    matrix_np = np.array(matrix, dtype=np.float32)  # Shape: (N, 128)
    
    # Vectorized cosine similarity: Matrix @ query_vec -> Shape: (N,)
    similarities = np.dot(matrix_np, query_vec)
    best_idx = int(np.argmax(similarities))
    best_similarity = float(similarities[best_idx])

    best_student_id, best_name, best_code, best_pose = metadata_list[best_idx]
    is_recognized = best_similarity >= match_threshold

    return {
        "student_id": best_student_id,
        "student_name": best_name,
        "student_code": best_code,
        "similarity": round(best_similarity, 3),
        "confidence": round(best_similarity, 3),
        "recognized": is_recognized,
        "pose": best_pose
    }
