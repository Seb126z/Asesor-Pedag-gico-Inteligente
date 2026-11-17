from pathlib import Path
from uuid import uuid4
import os
import zipfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import UPLOAD_DIR, MAX_UPLOAD_MB
from app.models.entities import Laboratory, Evidence, Evaluation
from app.schemas.contracts import RubricUpdate, EvaluationCreate, ApprovalUpdate
from app.services.rubrics import validate_rubric, calculate_grade

# Importar lector de PDF de forma segura
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

router = APIRouter(prefix="/api")

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
async def upload_evidence(laboratory_id: int, student: str = "Estudiante", file: UploadFile = File(...), db: Session = Depends(get_db)):
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

    # ==========================================
    # TU MÓDULO (JERÓNIMO): Procesamiento de Archivos
    # ==========================================
    file_ext = Path(safe_name).suffix.lower()
    file_analysis = {}

    # 1. Lectura de archivos PDF
    if file_ext == '.pdf' and PdfReader:
        try:
            reader = PdfReader(destination)
            pdf_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pdf_text += text + "\n"
            file_analysis["pdf_text_preview"] = pdf_text[:600] # Vista previa del contenido extraído
            file_analysis["total_characters"] = len(pdf_text)
        except Exception as e:
            file_analysis["pdf_error"] = str(e)

    # 2. Recepción y análisis de archivos ZIP / Código fuente
    elif file_ext == '.zip':
        try:
            extract_path = UPLOAD_DIR / f"extracted_{uuid4().hex}"
            with zipfile.ZipFile(destination, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            code_files = []
            for root, dirs, files in os.walk(extract_path):
                for f in files:
                    if f.endswith(('.py', '.js', '.java', '.cpp', '.txt', '.json', '.html', '.sql')):
                        code_files.append(f)
            
            file_analysis["zip_extracted"] = True
            file_analysis["code_files_found"] = code_files
            file_analysis["total_files_found"] = len(code_files)
        except Exception as e:
            file_analysis["zip_error"] = str(e)

    # Guardar registro en la Base de Datos
    record = Evidence(
        laboratory_id=laboratory_id, 
        student=student, 
        original_name=safe_name, 
        stored_name=stored, 
        content_type=file.content_type or "application/octet-stream"
    )
    db.add(record); db.commit(); db.refresh(record)
    
    return {
        "id": record.id, 
        "laboratory_id": laboratory_id, 
        "filename": record.original_name, 
        "size_bytes": size, 
        "message": "Evidencia almacenada y analizada correctamente",
        "file_analysis": file_analysis
    }

@router.get("/laboratories/{laboratory_id}/evidence")
def list_evidence(laboratory_id: int, db: Session = Depends(get_db)):
    return db.query(Evidence).filter(Evidence.laboratory_id == laboratory_id).order_by(Evidence.uploaded_at.desc()).all()

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
        raise HTTPException(422, "La cantidad de resultados no coincide con los criterios de la rúbrica")
    normalized = []
    for rubric_item, result_item in zip(lab.rubric, criteria_results):
        score = float(result_item.get("score", -1))
        if not 0 <= score <= 5:
            raise HTTPException(422, "Cada puntuación debe estar entre 0 y 5")
        normalized.append({"score": score, "weight": float(rubric_item["weight"])})
    
    backend_grade = calculate_grade(normalized)
    result_data = dict(payload.result)
    result_data["preliminary_grade"] = backend_grade
    record = Evaluation(
        laboratory_id=laboratory_id, 
        student=payload.student, 
        rubric_version=lab.rubric_version, 
        model_name=payload.model_name, 
        preliminary_grade=backend_grade, 
        result=result_data
    )
    db.add(record); db.commit(); db.refresh(record)
    return {"id": record.id, "preliminary_grade": record.preliminary_grade, "approved": record.approved}

@router.patch("/evaluations/{evaluation_id}/approval")
def approve_evaluation(evaluation_id: int, payload: ApprovalUpdate, db: Session = Depends(get_db)):
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
def list_evaluations(student: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Evaluation)
    if student:
        query = query.filter(Evaluation.student == student)
    return query.order_by(Evaluation.created_at.desc()).all()