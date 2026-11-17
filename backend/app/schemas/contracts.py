from pydantic import BaseModel, Field, ConfigDict
from typing import Any

class Criterion(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    weight: float = Field(ge=0, le=100)
    indicators: list[str] = []

class RubricUpdate(BaseModel):
    version: str = "1.0"
    criteria: list[Criterion]

class EvaluationCreate(BaseModel):
    student: str = "Estudiante"
    rubric_version: str
    model_name: str = "mock-local-v1"
    preliminary_grade: float = Field(ge=0, le=5)
    result: dict[str, Any]

class ApprovalUpdate(BaseModel):
    approved: bool
    final_grade: float | None = Field(default=None, ge=0, le=5)
    teacher_feedback: str | None = Field(default=None, max_length=4000)

class LaboratoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cohort: int
    name: str
    topics: list
    rubric_version: str
    rubric: list
    description: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(max_length=180, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
