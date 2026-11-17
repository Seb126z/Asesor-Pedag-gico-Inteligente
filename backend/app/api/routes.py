from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import UPLOAD_DIR, MAX_UPLOAD_MB
from app.models.entities import Laboratory, Evidence, Evaluation
from app.schemas.contracts import RubricUpdate, EvaluationCreate, ApprovalUpdate
from app.services.rubrics import validate_rubric, calculate_grade
from app.services.analytics import build_analytics_report, build_mindmap

router = APIRouter(prefix="/api")
ALLOWED_EXTENSIONS = {".pdf", ".zip", ".txt", ".py", ".js", ".html", ".docx",
                      ".pptx", ".png", ".jpg", ".jpeg", ".mp4"}


@router.get("/health")
def health():
    return {"status": "ok", "service": "asesor-pedagogico-api"}


@router.get("/laboratories")
def list_laboratories(db: Session = Depends(get_db)):
    return db.query(Laboratory).order_by(Laboratory.cohort, Laboratory.id).all()


@router.get("/laboratories/{laboratory_id}")
def get_laboratory(laboratory_id: int, db: Session = Depends(get_db)):
    item = db.get(Laboratory, laboratory_id)
    if not item:
        raise HTTPException(404, "Laboratorio no encontrado")
    return item


@router.put("/laboratories/{laboratory_id}/rubric")
def update_rubric(laboratory_id: int, payload: RubricUpdate, db: Session = Depends(get_db)):
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
async def upload_evidence(laboratory_id: int, student: str = "Estudiante",
                          file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not db.get(Laboratory, laboratory_id):
        raise HTTPException(404, "Laboratorio no encontrado")
    safe_name = Path(file.filename or "evidencia.bin").name
    if Path(safe_name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Tipo de archivo no permitido")
    if not student.strip() or len(student) > 160:
        raise HTTPException(422, "El nombre del estudiante debe tener entre 1 y 160 caracteres")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid4().hex}_{safe_name}"
    destination = UPLOAD_DIR / stored
    size = 0
    try:
        with destination.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_MB * 1024 * 1024:
                    raise HTTPException(413, f"El archivo supera {MAX_UPLOAD_MB} MB")
                out.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    record = Evidence(laboratory_id=laboratory_id, student=student.strip(),
                      original_name=safe_name, stored_name=stored,
                      content_type=file.content_type or "application/octet-stream")
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "laboratory_id": laboratory_id, "filename": record.original_name,
            "size_bytes": size, "message": "Evidencia almacenada"}


@router.get("/laboratories/{laboratory_id}/evidence")
def list_evidence(laboratory_id: int, db: Session = Depends(get_db)):
    if not db.get(Laboratory, laboratory_id):
        raise HTTPException(404, "Laboratorio no encontrado")
    return db.query(Evidence).filter(Evidence.laboratory_id == laboratory_id).order_by(
        Evidence.uploaded_at.desc()).all()


@router.get("/evidence/{evidence_id}/download")
def download_evidence(evidence_id: int, db: Session = Depends(get_db)):
    record = db.get(Evidence, evidence_id)
    if not record:
        raise HTTPException(404, "Evidencia no encontrada")
    path = (UPLOAD_DIR / record.stored_name).resolve()
    if not path.is_relative_to(UPLOAD_DIR.resolve()) or not path.is_file():
        raise HTTPException(404, "Archivo no disponible")
    return FileResponse(path, filename=record.original_name,
                        media_type="application/octet-stream")


@router.post("/laboratories/{laboratory_id}/evaluations")
def create_evaluation(laboratory_id: int, payload: EvaluationCreate,
                      db: Session = Depends(get_db)):
    lab = db.get(Laboratory, laboratory_id)
    if not lab:
        raise HTTPException(404, "Laboratorio no encontrado")
    check = validate_rubric(lab.rubric)
    if not check["valid"]:
        raise HTTPException(422, detail=check)
    if payload.rubric_version != lab.rubric_version:
        raise HTTPException(409, "La versión de rúbrica cambió. Actualiza y vuelve a evaluar.")
    criteria_results = payload.result.crit
    if len(criteria_results) != len(lab.rubric):
        raise HTTPException(422, "La cantidad de resultados no coincide con los criterios de la rúbrica")
    normalized = []
    for rubric_item, result_item in zip(lab.rubric, criteria_results):
        if result_item.criterio.strip().casefold() != rubric_item["name"].strip().casefold():
            raise HTTPException(422, "El nombre/orden de los criterios no coincide con la rúbrica vigente")
        normalized.append({"score": result_item.score, "weight": float(rubric_item["weight"])})
    backend_grade = calculate_grade(normalized)
    result_data = payload.result.model_dump()
    result_data["preliminary_grade"] = backend_grade
    record = Evaluation(laboratory_id=laboratory_id, student=payload.student.strip(),
                        rubric_version=lab.rubric_version, model_name=payload.model_name,
                        preliminary_grade=backend_grade, result=result_data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "preliminary_grade": record.preliminary_grade,
            "approved": record.approved}


@router.patch("/evaluations/{evaluation_id}/approval")
def approve_evaluation(evaluation_id: int, payload: ApprovalUpdate,
                       db: Session = Depends(get_db)):
    record = db.get(Evaluation, evaluation_id)
    if not record:
        raise HTTPException(404, "Evaluación no encontrada")
    if payload.approved and payload.final_grade is None:
        raise HTTPException(422, "La aprobación requiere una nota final")
    record.approved = payload.approved
    record.final_grade = payload.final_grade if payload.approved else None
    db.commit()
    return {"id": record.id, "approved": record.approved, "final_grade": record.final_grade}


@router.get("/evaluations")
def list_evaluations(student: str | None = None, laboratory_id: int | None = None,
                     approved: bool | None = None, db: Session = Depends(get_db)):
    query = db.query(Evaluation)
    if student:
        query = query.filter(Evaluation.student == student)
    if laboratory_id is not None:
        query = query.filter(Evaluation.laboratory_id == laboratory_id)
    if approved is not None:
        query = query.filter(Evaluation.approved == approved)
    return query.order_by(Evaluation.created_at.desc()).all()


@router.get("/analytics/summary")
def analytics_summary(cohort: int | None = None, student: str | None = None,
                      db: Session = Depends(get_db)):
    return build_analytics_report(db, cohort=cohort, student=student)


@router.get("/analytics/report")
def analytics_report(cohort: int | None = None, student: str | None = None,
                     db: Session = Depends(get_db)):
    """Informe consolidado basado únicamente en evaluaciones aprobadas por docente."""
    return build_analytics_report(db, cohort=cohort, student=student)


@router.get("/mindmap")
def mindmap_data(cohort: int | None = None, student: str | None = None,
                 db: Session = Depends(get_db)):
    """Grafo de laboratorios, temáticas y evidencias; incluye dominio cuando hay notas aprobadas."""
    return build_mindmap(db, cohort=cohort, student=student)
