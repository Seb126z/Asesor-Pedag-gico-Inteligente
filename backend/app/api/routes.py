from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_docente
from app.core.config import UPLOAD_DIR, MAX_UPLOAD_MB
from app.core.database import get_db
from app.models.entities import Laboratory, Evidence, Evaluation, User
from app.schemas.contracts import RubricUpdate, EvaluationCreate, ApprovalUpdate
from app.services.ai_evaluator import evaluar_evidencia_con_ia, default_model
from app.services.analytics import build_analytics_report, build_mindmap
from app.services.evidence_text import extract_text
from app.services.rubrics import validate_rubric, calculate_grade

router = APIRouter(prefix="/api")
ALLOWED_EXTENSIONS = {".pdf", ".zip", ".txt", ".py", ".js", ".html", ".docx",
                      ".pptx", ".png", ".jpg", ".jpeg", ".mp4"}


def _level(score: float) -> str:
    return ("Sobresaliente" if score >= 4.5 else "Alto" if score >= 3.5
            else "Básico" if score >= 2.5 else "Bajo" if score > 0 else "Sin evidencia")


def _student_scope(user: User) -> int | None:
    """Los estudiantes solo ven lo suyo (filtro por id de usuario); el docente ve todo."""
    return None if user.role == "docente" else user.id


# ----------------------------------------------------------------- salud y laboratorios
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
def update_rubric(laboratory_id: int, payload: RubricUpdate, db: Session = Depends(get_db),
                  _: User = Depends(require_docente)):
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


# ----------------------------------------------------------------- evidencias
@router.post("/laboratories/{laboratory_id}/evidence")
async def upload_evidence(laboratory_id: int, file: UploadFile = File(...), db: Session = Depends(get_db),
                          user: User = Depends(get_current_user)):
    if not db.get(Laboratory, laboratory_id):
        raise HTTPException(404, "Laboratorio no encontrado")
    safe_name = Path(file.filename or "evidencia.bin").name
    if Path(safe_name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Tipo de archivo no permitido")
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
    record = Evidence(laboratory_id=laboratory_id, student=user.name, student_id=user.id,
                      original_name=safe_name, stored_name=stored,
                      content_type=file.content_type or "application/octet-stream")
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "laboratory_id": laboratory_id, "filename": record.original_name,
            "size_bytes": size, "message": "Evidencia almacenada"}


@router.get("/laboratories/{laboratory_id}/evidence")
def list_evidence(laboratory_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not db.get(Laboratory, laboratory_id):
        raise HTTPException(404, "Laboratorio no encontrado")
    query = db.query(Evidence).filter(Evidence.laboratory_id == laboratory_id)
    scope = _student_scope(user)
    if scope is not None:
        query = query.filter(Evidence.student_id == scope)
    return query.order_by(Evidence.uploaded_at.desc()).all()


@router.get("/evidence/{evidence_id}/download")
def download_evidence(evidence_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.get(Evidence, evidence_id)
    scope = _student_scope(user)
    if not record or (scope is not None and record.student_id != scope):
        raise HTTPException(404, "Evidencia no encontrada")
    path = (UPLOAD_DIR / record.stored_name).resolve()
    if not path.is_relative_to(UPLOAD_DIR.resolve()) or not path.is_file():
        raise HTTPException(404, "Archivo no disponible")
    return FileResponse(path, filename=record.original_name, media_type="application/octet-stream")


# ----------------------------------------------------------------- evaluaciones
@router.post("/laboratories/{laboratory_id}/evaluations")
def create_evaluation(laboratory_id: int, payload: EvaluationCreate, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    lab = db.get(Laboratory, laboratory_id)
    if not lab:
        raise HTTPException(404, "Laboratorio no encontrado")
    check = validate_rubric(lab.rubric)
    if not check["valid"]:
        raise HTTPException(422, detail=check)
    if payload.rubric_version != lab.rubric_version:
        raise HTTPException(409, "La versión de rúbrica cambió. Actualiza y vuelve a evaluar.")
    criteria_results = payload.result.get("crit", [])
    if not isinstance(criteria_results, list) or len(criteria_results) != len(lab.rubric):
        raise HTTPException(422, "La cantidad de resultados no coincide con los criterios de la rúbrica oficial")

    normalized = []
    for rubric_item, result_item in zip(lab.rubric, criteria_results):
        if not isinstance(result_item, dict):
            raise HTTPException(422, "Cada resultado de criterio debe ser un objeto")
        name = result_item.get("criterio")
        if name is not None and str(name).strip().casefold() != rubric_item["name"].strip().casefold():
            raise HTTPException(422, "El nombre/orden de los criterios no coincide con la rúbrica vigente")
        try:
            score = float(result_item.get("score"))
        except (TypeError, ValueError):
            raise HTTPException(422, "Cada criterio necesita una puntuación numérica")
        if not 0 <= score <= 5:
            raise HTTPException(422, "Cada puntuación debe estar entre 0 y 5")
        normalized.append({"score": score, "weight": float(rubric_item["weight"])})

    # La nota la calcula siempre el backend con los pesos oficiales; se ignora la que envía el cliente.
    backend_grade = calculate_grade(normalized)
    result_data = dict(payload.result)
    result_data["preliminary_grade"] = backend_grade
    is_student = user.role == "estudiante"  # el estudiante siempre queda como autor; el docente puede indicar el nombre
    record = Evaluation(laboratory_id=laboratory_id,
                        student=user.name if is_student else payload.student.strip() or user.name,
                        student_id=user.id if is_student else None,
                        rubric_version=lab.rubric_version, model_name=payload.model_name,
                        preliminary_grade=backend_grade, result=result_data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "preliminary_grade": record.preliminary_grade, "approved": record.approved}


@router.post("/laboratories/{laboratory_id}/evaluations/ai-auto")
def create_ai_automated_evaluation(laboratory_id: int, student_id: int | None = None,
                                   model_name: str | None = None, db: Session = Depends(get_db),
                                   user: User = Depends(get_current_user)):
    """Evalúa con un LLM la última evidencia del estudiante; la nota la calcula el backend."""
    lab = db.get(Laboratory, laboratory_id)
    if not lab:
        raise HTTPException(404, "Laboratorio no encontrado")
    check = validate_rubric(lab.rubric)
    if not check["valid"]:
        raise HTTPException(422, detail={"error": "La rúbrica del laboratorio tiene inconsistencias", "details": check})

    target = user
    if user.role == "docente" and student_id is not None:
        target = db.get(User, student_id)
        if not target:
            raise HTTPException(404, "Estudiante no encontrado")

    evidence = (db.query(Evidence)
                .filter(Evidence.laboratory_id == laboratory_id, Evidence.student_id == target.id)
                .order_by(Evidence.uploaded_at.desc(), Evidence.id.desc()).first())
    if not evidence:
        raise HTTPException(422, "No hay evidencias cargadas para este laboratorio. Sube un archivo primero.")

    text, extracted = extract_text(UPLOAD_DIR / evidence.stored_name, evidence.original_name)
    if not extracted:
        raise HTTPException(422, text.strip("[]") + " Formatos admitidos: PDF con texto, .txt, .py, .js, .html.")
    model_name = model_name or default_model()
    ai = evaluar_evidencia_con_ia(text, lab.rubric, model_name)
    fallback = bool(ai.get("fallback"))
    by_name = {str(c.get("name", "")).strip().casefold(): c for c in ai.get("crit", [])}

    crit, normalized = [], []
    for rubric_item in lab.rubric:
        found = by_name.get(rubric_item["name"].strip().casefold())
        score = max(0.0, min(5.0, float(found["score"]))) if found else 0.0
        justification = found.get("justification") if found else "El modelo no evaluó este criterio."
        crit.append({"criterio": rubric_item["name"], "peso": rubric_item["weight"], "score": score,
                     "nivel": _level(score), "evidencia": justification,
                     "fortaleza": None, "brecha": None if found else "Criterio sin evaluar"})
        normalized.append({"score": score, "weight": float(rubric_item["weight"])})

    backend_grade = calculate_grade(normalized)
    used_model = "respaldo-sin-llm" if fallback else model_name
    result = {"laboratorio": lab.name, "version_rubrica": lab.rubric_version, "modelo": used_model,
              "fecha": datetime.utcnow().date().isoformat(), "summary": ai.get("summary"),
              "fallback_reason": ai.get("fallback_reason"),
              "strengths": ai.get("strengths", []), "weaknesses": ai.get("weaknesses", []),
              "verificacion": {"texto_extraido": extracted, "evidencia": evidence.original_name,
                               "sandbox": "no ejecutado en este prototipo"},
              "crit": crit, "preliminary_grade": backend_grade, "fallback": fallback}
    record = Evaluation(laboratory_id=laboratory_id, student=target.name, student_id=target.id,
                        rubric_version=lab.rubric_version, model_name=used_model,
                        preliminary_grade=backend_grade, result=result)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"status": "success", "evaluation_id": record.id, "student": target.name,
            "preliminary_grade": backend_grade, "fallback": fallback, "ai_analysis": result}


@router.patch("/evaluations/{evaluation_id}/approval")
def approve_evaluation(evaluation_id: int, payload: ApprovalUpdate, db: Session = Depends(get_db),
                       docente: User = Depends(require_docente)):
    record = db.get(Evaluation, evaluation_id)
    if not record:
        raise HTTPException(404, "Evaluación no encontrada")
    if payload.approved and payload.final_grade is None:
        raise HTTPException(422, "La aprobación docente requiere especificar una nota final")
    record.approved = payload.approved
    record.final_grade = payload.final_grade if payload.approved else None
    if payload.teacher_feedback is not None:
        record.teacher_feedback = payload.teacher_feedback
    record.approved_by = docente.id if payload.approved else None
    record.approved_at = datetime.utcnow() if payload.approved else None
    db.commit()
    return {"id": record.id, "approved": record.approved, "final_grade": record.final_grade,
            "teacher_feedback": record.teacher_feedback}


@router.get("/evaluations")
def list_evaluations(student: str | None = None, laboratory_id: int | None = None,
                     approved: bool | None = None, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    query = db.query(Evaluation)
    if user.role == "docente":
        if student:
            query = query.filter(Evaluation.student == student)
        if approved is not None:
            query = query.filter(Evaluation.approved == approved)
    else:  # el estudiante solo ve sus evaluaciones ya aprobadas y publicadas
        query = query.filter(Evaluation.student_id == user.id, Evaluation.approved.is_(True))
    if laboratory_id is not None:
        query = query.filter(Evaluation.laboratory_id == laboratory_id)
    return query.order_by(Evaluation.created_at.desc(), Evaluation.id.desc()).all()


@router.get("/evaluations/{evaluation_id}")
def get_evaluation(evaluation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.get(Evaluation, evaluation_id)
    if not record or (user.role != "docente" and not (record.student_id == user.id and record.approved)):
        raise HTTPException(404, "Evaluación no encontrada")
    return record


# ----------------------------------------------------------------- analítica
@router.get("/analytics/summary")
def analytics_summary(cohort: int | None = None, student: str | None = None, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    return build_analytics_report(db, cohort=cohort, student=student, student_id=_student_scope(user))


@router.get("/analytics/report")
def analytics_report(cohort: int | None = None, student: str | None = None, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Informe consolidado basado únicamente en evaluaciones aprobadas por docente."""
    return build_analytics_report(db, cohort=cohort, student=student, student_id=_student_scope(user))


@router.get("/mindmap")
def mindmap_data(cohort: int | None = None, student: str | None = None, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """Grafo de laboratorios, temáticas y evidencias; incluye dominio cuando hay notas aprobadas."""
    return build_mindmap(db, cohort=cohort, student=student, student_id=_student_scope(user))
