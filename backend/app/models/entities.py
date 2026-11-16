from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Student(Base):
    __tablename__ = "students"
    
    id: Mapped[str] = mapped_column(String(160), primary_key=True) # Código o correo institucional del estudiante
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    evidences = relationship("Evidence", back_populates="student_rel")
    evaluations = relationship("Evaluation", back_populates="student_rel")

class Laboratory(Base):
    __tablename__ = "laboratories"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cohort: Mapped[int] = mapped_column(Integer, default=1)
    name: Mapped[str] = mapped_column(String(180))
    topics: Mapped[list] = mapped_column(JSON, default=list)
    rubric_version: Mapped[str] = mapped_column(String(20), default="1.0")
    rubric: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    
    evaluations = relationship("Evaluation", back_populates="laboratory")
    evidences = relationship("Evidence", back_populates="laboratory")

class Evidence(Base):
    __tablename__ = "evidences"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    laboratory_id: Mapped[int] = mapped_column(ForeignKey("laboratories.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id")) # Relación con la nueva tabla de estudiantes
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    laboratory = relationship("Laboratory", back_populates="evidences")
    student_rel = relationship("Student", back_populates="evidences")

class Evaluation(Base):
    __tablename__ = "evaluations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    laboratory_id: Mapped[int] = mapped_column(ForeignKey("laboratories.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id")) # Relación con la nueva tabla de estudiantes
    rubric_version: Mapped[str] = mapped_column(String(20))
    model_name: Mapped[str] = mapped_column(String(120), default="mock-local-v1")
    preliminary_grade: Mapped[float] = mapped_column(Float)
    final_grade: Mapped[float | None] = mapped_column(Float, nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    laboratory = relationship("Laboratory", back_populates="evaluations")
    student_rel = relationship("Student", back_populates="evaluations")