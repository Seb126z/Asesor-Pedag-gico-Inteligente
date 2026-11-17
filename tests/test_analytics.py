from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.entities import Laboratory, Evaluation, Evidence
from app.services.analytics import build_analytics_report, build_mindmap


def make_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed(db):
    lab = Laboratory(id=1, cohort=1, name="Laboratorio de búsqueda", topics=["busqueda"],
                     rubric_version="1.0", rubric=[{"name": "Algoritmos", "weight": 100}])
    db.add(lab)
    db.add(Evidence(laboratory_id=1, student="Ana", original_name="solucion.pdf",
                    stored_name="stored.pdf", content_type="application/pdf"))
    db.add(Evaluation(laboratory_id=1, student="Ana", rubric_version="1.0", model_name="test",
                      preliminary_grade=4.0, final_grade=4.0, approved=True,
                      result={"crit": [{"criterio": "Algoritmos", "score": 4.0}]}))
    db.add(Evaluation(laboratory_id=1, student="Luis", rubric_version="1.0", model_name="test",
                      preliminary_grade=2.0, final_grade=None, approved=False,
                      result={"crit": [{"criterio": "Algoritmos", "score": 2.0}]}))
    db.commit()


def test_report_uses_only_approved_evaluations():
    db = make_db()
    try:
        seed(db)
        result = build_analytics_report(db)
        assert result["totals"]["evaluations"] == 2
        assert result["totals"]["approved_evaluations"] == 1
        assert result["totals"]["average_grade"] == 4.0
        assert result["strengths"][0]["criterion"] == "Algoritmos"
        assert result["laboratories"][0]["evidence_count"] == 1
    finally:
        db.close()


def test_report_can_filter_by_student_and_cohort():
    db = make_db()
    try:
        seed(db)
        result = build_analytics_report(db, cohort=1, student="Ana")
        assert result["totals"]["approved_evaluations"] == 1
        assert result["totals"]["average_grade"] == 4.0
        assert build_analytics_report(db, cohort=2)["totals"]["laboratories"] == 0
    finally:
        db.close()


def test_mindmap_contains_topics_labs_and_evidence():
    db = make_db()
    try:
        seed(db)
        result = build_mindmap(db)
        node_types = {node["type"] for node in result["nodes"]}
        assert {"root", "laboratory", "topic", "evidence"}.issubset(node_types)
        topic = next(node for node in result["nodes"] if node["type"] == "topic")
        assert topic["mastery"] == 4.0
        assert any(edge["type"] == "evidence" for edge in result["edges"])
    finally:
        db.close()
