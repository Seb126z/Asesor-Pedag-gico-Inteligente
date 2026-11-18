"""Evaluaciones: registro manual, evaluación automática con IA y aprobación docente."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_or_404, is_docente, require_docente
from app.api.laboratories import LAB_NOT_FOUND
from app.core.clock import utcnow
from app.core.config import UPLOAD_DIR
from app.core.database import get_db
from app.models.entities import Evaluation, Evidence, Laboratory, User
from app.schemas.contracts import ApprovalUpdate, EvaluationCreate
from app.services.ai_evaluator import default_model, evaluar_evidencia_con_ia
from app.services.evidence_text import extract_text
from app.services.grading import InvalidResult, build_ai_result, grade_manual_result
from app.services.rubrics import validate_rubric

router = APIRouter(tags=["evaluaciones"])
EVAL_NOT_FOUND = "Evaluación no encontrada"


def _save(db: Session, record: Evaluation) -> Evaluation:
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/laboratories/{laboratory_id}/evaluations")
def create_evaluation(laboratory_id: int, payload: EvaluationCreate, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    lab = get_or_404(db, Laboratory, laboratory_id, LAB_NOT_FOUND)
    check = validate_rubric(lab.rubric)
    if not check["valid"]:
        raise HTTPException(422, detail=check)
    if payload.rubric_version != lab.rubric_version:
        raise HTTPException(409, "La versión de rúbrica cambió. Actualiza y vuelve a evaluar.")
    try:
        # La nota la calcula siempre el backend con los pesos oficiales; se ignora la que envía el cliente.
        grade = grade_manual_result(lab.rubric, payload.result.get("crit", []))
    except InvalidResult as exc:
        raise HTTPException(422, str(exc)) from None

    # El estudiante siempre queda como autor; el docente puede indicar el nombre.
    student_name = (payload.student.strip() or user.name) if is_docente(user) else user.name
    record = _save(db, Evaluation(laboratory_id=laboratory_id, student=student_name,
                                  student_id=None if is_docente(user) else user.id,
                                  rubric_version=lab.rubric_version, model_name=payload.model_name,
                                  preliminary_grade=grade, result={**payload.result, "preliminary_grade": grade}))
    return {"id": record.id, "preliminary_grade": record.preliminary_grade, "approved": record.approved}


@router.post("/laboratories/{laboratory_id}/evaluations/ai-auto")
def create_ai_automated_evaluation(laboratory_id: int, student_id: int | None = None,
                                   model_name: str | None = None, db: Session = Depends(get_db),
                                   user: User = Depends(get_current_user)):
    """Evalúa con un LLM la última evidencia del estudiante; la nota la calcula el backend."""
    lab = get_or_404(db, Laboratory, laboratory_id, LAB_NOT_FOUND)
    check = validate_rubric(lab.rubric)
    if not check["valid"]:
        raise HTTPException(422, detail={"error": "La rúbrica del laboratorio tiene inconsistencias", "details": check})

    target = user
    if is_docente(user) and student_id is not None:
        target = get_or_404(db, User, student_id, "Estudiante no encontrado")

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
    result = build_ai_result(lab, ai, evidence.original_name, extracted, model_name)
    record = _save(db, Evaluation(laboratory_id=laboratory_id, student=target.name, student_id=target.id,
                                  rubric_version=lab.rubric_version, model_name=result["modelo"],
                                  preliminary_grade=result["preliminary_grade"], result=result))
    return {"status": "success", "evaluation_id": record.id, "student": target.name,
            "preliminary_grade": record.preliminary_grade, "fallback": result["fallback"], "ai_analysis": result}


@router.patch("/evaluations/{evaluation_id}/approval")
def approve_evaluation(evaluation_id: int, payload: ApprovalUpdate, db: Session = Depends(get_db),
                       docente: User = Depends(require_docente)):
    record = get_or_404(db, Evaluation, evaluation_id, EVAL_NOT_FOUND)
    if payload.approved and payload.final_grade is None:
        raise HTTPException(422, "La aprobación docente requiere especificar una nota final")
    record.approved = payload.approved
    record.final_grade = payload.final_grade if payload.approved else None
    if payload.teacher_feedback is not None:
        record.teacher_feedback = payload.teacher_feedback
    record.approved_by = docente.id if payload.approved else None
    record.approved_at = utcnow() if payload.approved else None
    db.commit()
    return {"id": record.id, "approved": record.approved, "final_grade": record.final_grade,
            "teacher_feedback": record.teacher_feedback}


@router.get("/evaluations")
def list_evaluations(student: str | None = None, laboratory_id: int | None = None,
                     approved: bool | None = None, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    query = db.query(Evaluation)
    if is_docente(user):
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
    visible = record and (is_docente(user) or (record.student_id == user.id and record.approved))
    if not visible:
        raise HTTPException(404, EVAL_NOT_FOUND)
    return record
