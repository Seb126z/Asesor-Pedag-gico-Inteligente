from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import UPLOAD_DIR, MAX_UPLOAD_MB
from app.models.entities import Laboratory, Evidence, Evaluation, Student
from app.schemas.contracts import RubricUpdate, EvaluationCreate, ApprovalUpdate
from app.services.rubrics import validate_rubric, calculate_grade
from app.services.ai_evaluator import evaluar_evidencia_con_ia

router = APIRouter(prefix="/api")

@router.get("/health")
def health():
    return {"status": "ok", "service": "asesor-pedagogico-api", "owner": "Backend Team - Nicolas"}

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
async def upload_evidence(laboratory_id: int, student: str = "Estudiante", file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not db.get(Laboratory, laboratory_id):
        raise HTTPException(404, "Laboratorio no encontrado")
    
    # Aseguramos que el estudiante exista en la tabla de estudiantes
    student_record = db.get(Student, student)
    if not student_record:
        student_record = Student(id=student, name=student)
        db.add(student_record)
        db.commit()

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
            
    record = Evidence(
        laboratory_id=laboratory_id, 
        student_id=student, 
        original_name=safe_name, 
        stored_name=stored, 
        content_type=file.content_type or "application/octet-stream"
    )
    db.add(record); db.commit(); db.refresh(record)
    return {"id": record.id, "laboratory_id": laboratory_id, "filename": record.original_name, "size_bytes": size, "message": "Evidencia almacenada con éxito"}

@router.get("/laboratories/{laboratory_id}/evidence")
def list_evidence(laboratory_id: int, db: Session = Depends(get_db)):
    return db.query(Evidence).filter(Evidence.laboratory_id == laboratory_id).order_by(Evidence.uploaded_at.desc()).all()

# Endpoint tradicional de evaluación manual
@router.post("/laboratories/{laboratory_id}/evaluations")
def create_evaluation(laboratory_id: int, payload: EvaluationCreate, db: Session = Depends(get_db)):
    lab = db.get(Laboratory, laboratory_id)
    if not lab:
        raise HTTPException(404, "Laboratorio no encontrado")
    
    check = validate_rubric(lab.rubric)
    if not check["valid"]:
        raise HTTPException(422, detail=check)
        
    criteria_results = payload.result.get("crit", [])
    if len(criteria_results) != len(lab.rubric):
        raise HTTPException(422, "La cantidad de resultados no coincide con los criterios de la rúbrica oficial")
        
    normalized = []
    for rubric_item, result_item in zip(lab.rubric, criteria_results):
        score = float(result_item.get("score", -1))
        if not 0 <= score <= 5:
            raise HTTPException(422, "Cada puntuación debe estar estrictamente entre 0 y 5")
        normalized.append({"score": score, "weight": float(rubric_item["weight"])})
        
    # CÁLCULO DETERMINISTA: El backend procesa las notas matemáticamente
    backend_grade = calculate_grade(normalized)
    result_data = dict(payload.result)
    result_data["preliminary_grade"] = backend_grade
    
    record = Evaluation(
        laboratory_id=laboratory_id, 
        student_id=payload.student, 
        rubric_version=lab.rubric_version, 
        model_name=payload.model_name, 
        preliminary_grade=backend_grade, 
        result=result_data
    )
    db.add(record); db.commit(); db.refresh(record)
    return {"id": record.id, "preliminary_grade": record.preliminary_grade, "approved": record.approved}

# NUEVO ENDPOINT AUTOMATIZADO: Conecta la IA, usa Pydantic y calcula la nota matemáticamente (Tareas 4 y 5)
@router.post("/laboratories/{laboratory_id}/evaluations/ai-auto")
def create_ai_automated_evaluation(laboratory_id: int, student_id: str, model_name: str = "llama3.2", db: Session = Depends(get_db)):
    lab = db.get(Laboratory, laboratory_id)
    if not lab:
        raise HTTPException(404, "Laboratorio no encontrado")
    
    # Validamos que la rúbrica esté correcta antes de invocar la IA
    check = validate_rubric(lab.rubric)
    if not check["valid"]:
        raise HTTPException(422, detail={"error": "La rúbrica del laboratorio tiene inconsistencias", "details": check})
    
    # Buscamos la última evidencia subida por este estudiante para este laboratorio
    evidencia = db.query(Evidence).filter(
        Evidence.laboratory_id == laboratory_id, 
        Evidence.student_id == student_id
    ).order_by(Evidence.uploaded_at.desc()).first()
    
    texto_evidencia_simulado = f"Evidencia del estudiante {student_id} para el laboratorio {lab.name}. Archivo base analizado con éxito."
    if evidencia:
        texto_evidencia_simulado = f"Archivo analizado: {evidencia.original_name} (Tipo: {evidencia.content_type})"

    # 1. Llamada a la IA asegurando respuesta con formato estructurado (Tareas 4 y 5)
    resultado_ia_json = evaluar_evidencia_con_ia(texto_evidencia_simulado, lab.rubric, model_name)
    
    criteria_results = resultado_ia_json.get("crit", [])
    
    # 2. Normalización para el cálculo determinista
    normalized = []
    for rubric_item in lab.rubric:
        # Buscamos el puntaje que la IA le dio a este criterio específico por su nombre
        matched_score = 3.0 # Valor por defecto seguro
        for res_item in criteria_results:
            if str(res_item.get("name", "")).strip().lower() == str(rubric_item.get("name", "")).strip().lower():
                matched_score = float(res_item.get("score", 3.0))
                break
        normalized.append({"score": matched_score, "weight": float(rubric_item["weight"])})

    # 3. Cálculo matemático definitivo de la nota por el backend
    backend_grade = calculate_grade(normalized)
    resultado_ia_json["preliminary_grade"] = backend_grade

    # 4. Guardamos el resultado en la base de datos de PostgreSQL
    record = Evaluation(
        laboratory_id=laboratory_id,
        student_id=student_id,
        rubric_version=lab.rubric_version,
        model_name=model_name,
        preliminary_grade=backend_grade,
        result=resultado_ia_json
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "status": "success",
        "evaluation_id": record.id,
        "student": student_id,
        "preliminary_grade": backend_grade,
        "ai_analysis": resultado_ia_json
    }

@router.patch("/evaluations/{evaluation_id}/approval")
def approve_evaluation(evaluation_id: int, payload: ApprovalUpdate, db: Session = Depends(get_db)):
    record = db.get(Evaluation, evaluation_id)
    if not record:
        raise HTTPException(404, "Evaluación no encontrada")
    if payload.approved and payload.final_grade is None:
        raise HTTPException(422, "La aprobación docente requiere especificar una nota final")
    record.approved = payload.approved
    record.final_grade = payload.final_grade if payload.approved else None
    db.commit()
    return {"id": record.id, "approved": record.approved, "final_grade": record.final_grade}

@router.get("/evaluations")
def list_evaluations(student: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Evaluation)
    if student:
        query = query.filter(Evaluation.student_id == student)
    return query.order_by(Evaluation.created_at.desc()).all()