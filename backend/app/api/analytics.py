"""Informes de analítica y mapa mental de competencias."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, student_scope
from app.core.database import get_db
from app.models.entities import User
from app.services.analytics import build_analytics_report, build_mindmap

router = APIRouter(tags=["analitica"])


@router.get("/analytics/report")
@router.get("/analytics/summary")  # alias conservado por compatibilidad
def analytics_report(cohort: int | None = None, student: str | None = None, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Informe consolidado basado únicamente en evaluaciones aprobadas por docente."""
    return build_analytics_report(db, cohort=cohort, student=student, student_id=student_scope(user))


@router.get("/mindmap")
def mindmap_data(cohort: int | None = None, student: str | None = None, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """Grafo de laboratorios, temáticas y evidencias; incluye dominio cuando hay notas aprobadas."""
    return build_mindmap(db, cohort=cohort, student=student, student_id=student_scope(user))
