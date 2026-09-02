import json
from datetime import datetime, timezone
from typing import List
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.base import Base

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Store embedding representation
    # embedding_vector is stored as pgvector Vector(128) if PostgreSQL or serialized JSON in sqlite
    embedding_json = Column(Text, nullable=False)
    
    pose = Column(String(50), default="frontal", nullable=False)
    quality_score = Column(Float, nullable=False, default=1.0)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student = relationship("Student", back_populates="face_embeddings")

    def get_embedding(self) -> List[float]:
        """Return embedding as list of floats."""
        return json.loads(self.embedding_json)

    def set_embedding(self, vector: List[float]) -> None:
        """Store embedding from list of floats."""
        self.embedding_json = json.dumps([float(x) for x in vector])

    def __repr__(self):
        return f"<FaceEmbedding(id={self.id}, student_id={self.student_id}, pose='{self.pose}', quality={self.quality_score:.2f})>"
