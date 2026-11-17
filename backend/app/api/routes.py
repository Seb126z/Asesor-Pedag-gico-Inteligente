from datetime import datetime
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import UPLOAD_DIR, MAX_UPLOAD_MB
from app.models.entities import Laboratory, Evidence, Evaluation, User
from app.api.deps import get_current_user, require_docente
from app.schemas.contracts import RubricUpdate, EvaluationCreate, ApprovalUpdate
from app.services.rubrics import validate_rubric, calculate_grade

router = APIRouter(prefix="/api")

@router.get("/health")
def health():
    return {"status": "ok", "service": "asesor-pedagogico-api"}

@router.get("/laboratories")
def list_laboratories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Laboratory).order_by(Laboratory.cohort, Laboratory.id).all()

@router.get("/laboratories/{laboratory_id}")
def get_laboratory(laboratory_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.get(Laboratory, laboratory_id)
    if not item:
        raise HTTPException(404, "Laboratorio no encontrado")
    return item

@router.put("/laboratories/{laboratory_id}/rubric")
def update_rubric(laboratory_id: int, payload: RubricUpdate, db: Session = Depends(get_db), _: User = Depends(require_docente)):
    item = db.get(Laboratory, laboratory_id)
    if not item:
        raise HTTPException(404, "Laboratorio no encontrado")
    criteria = [criterion.model_dump() for criterion in payload.criteria]
    validation = validate_rubric(criteria)
    if not validation["valid"]:
        raise HTTPException(422, detail=validation)
    item.rubric = criteria
    item.rubric_version = payload.version
    db.commit()
    return {"laboratory_id": item.id, "version": item.rubric_version, **validation}

@router.post("/laboratories/{laboratory_id}/evidence")
async def upload_evidence(laboratory_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not db.get(Laboratory, laboratory_id):
        raise HTTPException(404, "Laboratorio no encontrado")
    safe_name = Path(file.filename or "evidencia.bin").name
    allowed = {".pdf", ".zip", ".txt", ".py", ".js", ".html", ".docx", ".pptx", ".png", ".jpg", ".jpeg", ".mp4"}
    if Path(safe_name).suffix.lower() not in allowed:
        raise HTTPException(415, "Tipo de archivo no permitido")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid4().hex}_{safe_name}"
    destination = UPLOAD_DIR / stored
    size = 0
    with destination.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_MB * 1024 * 1024:
                out.close(); destination.unlink(missing_ok=True)
                raise HTTPException(413, f"El archivo supera {MAX_UPLOAD_MB} MB")
            out.write(chunk)
    record = Evidence(laboratory_id=laboratory_id, student=user.name, student_id=user.id, original_name=safe_name, stored_name=stored, content_type=file.content_type or "application/octet-stream")
    db.add(record); db.commit(); db.refresh(record)
    return {"id": record.id, "laboratory_id": laboratory_id, "filename": record.original_name, "size_bytes": size, "message": "Evidencia almacenada"}

@router.get("/laboratories/{laboratory_id}/evidence")
def list_evidence(laboratory_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Evidence).filter(Evidence.laboratory_id == laboratory_id)
    if user.role != "docente":
        query = query.filter(Evidence.student_id == user.id)
    return query.order_by(Evidence.uploaded_at.desc()).all()

@router.post("/laboratories/{laboratory_id}/evaluations")
def create_evaluation(laboratory_id: int, payload: EvaluationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lab = db.get(Laboratory, laboratory_id)
    if not lab:
        raise HTTPException(404, "Laboratorio no encontrado")
    check = validate_rubric(lab.rubric)
    if not check["valid"]:
        raise HTTPException(422, detail=check)
    criteria_results = payload.result.get("crit", [])
    if len(criteria_results) != len(lab.rubric):
        raise HTTPException(422, "La cantidad de resultados no coincide con los criterios de la rúbrica")
    normalized = []
    for rubric_item, result_item in zip(lab.rubric, criteria_results):
        score = float(result_item.get("score", -1))
        if not 0 <= score <= 5:
            raise HTTPException(422, "Cada puntuación debe estar entre 0 y 5")
        normalized.append({"score": score, "weight": float(rubric_item["weight"])})
    # La nota se recalcula aquí con los pesos oficiales; no se confía en la nota enviada por el cliente.
    backend_grade = calculate_grade(normalized)
    result_data = dict(payload.result)
    result_data["preliminary_grade"] = backend_grade
    is_student = user.role == "estudiante"  # el estudiante siempre queda como autor; el docente puede indicar el nombre
    record = Evaluation(laboratory_id=laboratory_id, student=user.name if is_student else payload.student, student_id=user.id if is_student else None, rubric_version=lab.rubric_version, model_name=payload.model_name, preliminary_grade=backend_grade, result=result_data)
    db.add(record); db.commit(); db.refresh(record)
    return {"id": record.id, "preliminary_grade": record.preliminary_grade, "approved": record.approved}

@router.patch("/evaluations/{evaluation_id}/approval")
def approve_evaluation(evaluation_id: int, payload: ApprovalUpdate, db: Session = Depends(get_db), docente: User = Depends(require_docente)):
    record = db.get(Evaluation, evaluation_id)
    if not record:
        raise HTTPException(404, "Evaluación no encontrada")
    if payload.approved and payload.final_grade is None:
        raise HTTPException(422, "La aprobación requiere una nota final")
    record.approved = payload.approved
    record.final_grade = payload.final_grade if payload.approved else None
    if payload.teacher_feedback is not None:
        record.teacher_feedback = payload.teacher_feedback
    record.approved_by = docente.id if payload.approved else None
    record.approved_at = datetime.utcnow() if payload.approved else None
    db.commit()
    return {"id": record.id, "approved": record.approved, "final_grade": record.final_grade, "teacher_feedback": record.teacher_feedback}

@router.get("/evaluations")
def list_evaluations(student: str | None = None, approved: bool | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Evaluation)
    if user.role == "docente":
        if student:
            query = query.filter(Evaluation.student == student)
        if approved is not None:
            query = query.filter(Evaluation.approved == approved)
    else:  # el estudiante solo ve sus evaluaciones ya aprobadas y publicadas
        query = query.filter(Evaluation.student_id == user.id, Evaluation.approved.is_(True))
    return query.order_by(Evaluation.created_at.desc()).all()

@router.get("/evaluations/{evaluation_id}")
def get_evaluation(evaluation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.get(Evaluation, evaluation_id)
    if not record or (user.role != "docente" and not (record.student_id == user.id and record.approved)):
        raise HTTPException(404, "Evaluación no encontrada")
    return record

