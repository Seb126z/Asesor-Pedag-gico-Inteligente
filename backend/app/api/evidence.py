"""Carga, listado y descarga de evidencias."""
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_or_404, student_scope
from app.api.laboratories import LAB_NOT_FOUND
from app.core.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_MB, UPLOAD_DIR
from app.core.database import get_db
from app.models.entities import Evidence, Laboratory, User
from app.services.evidence_text import analyze_upload

router = APIRouter(tags=["evidencias"])
CHUNK_BYTES = 1024 * 1024


async def _store_upload(file: UploadFile, destination: Path) -> int:
    """Guarda el archivo por bloques y corta si supera el límite. Devuelve el tamaño en bytes."""
    limit = MAX_UPLOAD_MB * 1024 * 1024
    size = 0
    try:
        with destination.open("wb") as out:
            while chunk := await file.read(CHUNK_BYTES):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, f"El archivo supera {MAX_UPLOAD_MB} MB")
                out.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    return size


@router.post("/laboratories/{laboratory_id}/evidence")
async def upload_evidence(laboratory_id: int, file: UploadFile = File(...), db: Session = Depends(get_db),
                          user: User = Depends(get_current_user)):
    get_or_404(db, Laboratory, laboratory_id, LAB_NOT_FOUND)
    safe_name = Path(file.filename or "evidencia.bin").name
    if Path(safe_name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Tipo de archivo no permitido")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid4().hex}_{safe_name}"
    destination = UPLOAD_DIR / stored
    size = await _store_upload(file, destination)

    record = Evidence(laboratory_id=laboratory_id, student=user.name, student_id=user.id,
                      original_name=safe_name, stored_name=stored,
                      content_type=file.content_type or "application/octet-stream")
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "laboratory_id": laboratory_id, "filename": record.original_name,
            "size_bytes": size, "message": "Evidencia almacenada",
            "file_analysis": analyze_upload(destination, safe_name)}


@router.get("/laboratories/{laboratory_id}/evidence")
def list_evidence(laboratory_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_or_404(db, Laboratory, laboratory_id, LAB_NOT_FOUND)
    query = db.query(Evidence).filter(Evidence.laboratory_id == laboratory_id)
    scope = student_scope(user)
    if scope is not None:
        query = query.filter(Evidence.student_id == scope)
    return query.order_by(Evidence.uploaded_at.desc()).all()


@router.get("/evidence/{evidence_id}/download")
def download_evidence(evidence_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.get(Evidence, evidence_id)
    scope = student_scope(user)
    if not record or (scope is not None and record.student_id != scope):
        raise HTTPException(404, "Evidencia no encontrada")
    path = (UPLOAD_DIR / record.stored_name).resolve()
    if not path.is_relative_to(UPLOAD_DIR.resolve()) or not path.is_file():
        raise HTTPException(404, "Archivo no disponible")
    return FileResponse(path, filename=record.original_name, media_type="application/octet-stream")
