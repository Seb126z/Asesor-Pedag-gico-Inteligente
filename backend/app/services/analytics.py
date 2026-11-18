"""Informe consolidado y mapa mental. Solo las evaluaciones aprobadas por el docente cuentan para las notas."""
from collections import defaultdict
from statistics import mean

from app.models.entities import Evaluation, Evidence, Laboratory

GAP_THRESHOLD = 3.5


def _avg(values: list[float]) -> float | None:
    return round(mean(values), 2) if values else None


def _labs(db, cohort: int | None) -> list[Laboratory]:
    query = db.query(Laboratory)
    if cohort is not None:
        query = query.filter(Laboratory.cohort == cohort)
    return query.order_by(Laboratory.cohort, Laboratory.id).all()


def _scoped(db, model, lab_ids: set[int], student: str | None, student_id: int | None):
    """Consulta de `model` (Evaluation o Evidence) limitada a los laboratorios y al estudiante indicados."""
    query = db.query(model).filter(model.laboratory_id.in_(lab_ids))
    if student:
        query = query.filter(model.student == student)
    if student_id is not None:
        query = query.filter(model.student_id == student_id)
    return query


def _is_graded(ev: Evaluation) -> bool:
    return bool(ev.approved) and ev.final_grade is not None


def build_analytics_report(db, cohort: int | None = None, student: str | None = None, student_id: int | None = None):
    labs = _labs(db, cohort)
    labs_by_id = {lab.id: lab for lab in labs}
    lab_ids = set(labs_by_id)

    evaluations = (_scoped(db, Evaluation, lab_ids, student, student_id)
                   .order_by(Evaluation.created_at.asc()).all())
    approved = [ev for ev in evaluations if _is_graded(ev)]
    evidences = _scoped(db, Evidence, lab_ids, student, student_id).all()

    approved_by_lab = defaultdict(list)
    for ev in approved:
        approved_by_lab[ev.laboratory_id].append(ev)
    evidence_count = defaultdict(int)
    for evidence in evidences:
        evidence_count[evidence.laboratory_id] += 1

    lab_rows = []
    criterion_scores = defaultdict(list)
    for lab in labs:
        lab_evals = approved_by_lab[lab.id]
        for ev in lab_evals:
            for item in (ev.result or {}).get("crit", []):
                name = str(item.get("criterio", "")).strip()
                if name and item.get("score") is not None:
                    criterion_scores[(lab.id, name)].append(float(item["score"]))
        lab_rows.append({
            "laboratory_id": lab.id, "laboratory": lab.name, "cohort": lab.cohort, "topics": lab.topics or [],
            "evaluations": len(lab_evals), "evidence_count": evidence_count[lab.id],
            "average_grade": _avg([float(ev.final_grade) for ev in lab_evals]),
        })

    gaps, strengths = [], []
    for (lab_id, criterion), scores in criterion_scores.items():
        item = {"laboratory_id": lab_id, "laboratory": labs_by_id[lab_id].name, "criterion": criterion,
                "average_score": _avg(scores), "sample_size": len(scores)}
        (gaps if item["average_score"] < GAP_THRESHOLD else strengths).append(item)
    strengths.sort(key=lambda x: x["average_score"], reverse=True)
    gaps.sort(key=lambda x: x["average_score"])

    cohort_rows = []
    for cohort_id in sorted({lab.cohort for lab in labs}):
        cohort_lab_ids = {lab.id for lab in labs if lab.cohort == cohort_id}
        cohort_evals = [ev for ev in approved if ev.laboratory_id in cohort_lab_ids]
        cohort_rows.append({"cohort": cohort_id, "laboratories": len(cohort_lab_ids),
                            "approved_evaluations": len(cohort_evals),
                            "average_grade": _avg([float(ev.final_grade) for ev in cohort_evals])})

    return {
        "filters": {"cohort": cohort, "student": student},
        "totals": {"laboratories": len(labs), "evaluations": len(evaluations),
                   "approved_evaluations": len(approved), "evidences": len(evidences),
                   "average_grade": _avg([float(ev.final_grade) for ev in approved])},
        "cohorts": cohort_rows,
        "laboratories": lab_rows,
        "strengths": strengths,
        "gaps": gaps,
        "recommendations": [
            {**gap, "recommendation": f"Reforzar {gap['criterion'].lower()} mediante ejercicios guiados "
                                      f"y una nueva evidencia para {gap['laboratory']}."}
            for gap in gaps
        ],
    }


def build_mindmap(db, cohort: int | None = None, student: str | None = None, student_id: int | None = None):
    labs = _labs(db, cohort)
    labs_by_id = {lab.id: lab for lab in labs}
    lab_ids = set(labs_by_id)
    evaluations = [ev for ev in _scoped(db, Evaluation, lab_ids, student, student_id)
                   .filter(Evaluation.approved.is_(True)).all() if _is_graded(ev)]
    evidences = _scoped(db, Evidence, lab_ids, student, student_id).all()

    topic_labs = defaultdict(set)
    topic_scores = defaultdict(list)
    lab_scores = defaultdict(list)
    evidence_count = defaultdict(int)
    for lab in labs:
        for topic in lab.topics or []:
            topic_labs[str(topic)].add(lab.id)
    for ev in evaluations:
        lab_scores[ev.laboratory_id].append(float(ev.final_grade))
        for topic in labs_by_id[ev.laboratory_id].topics or []:
            topic_scores[str(topic)].append(float(ev.final_grade))
    for evidence in evidences:
        evidence_count[evidence.laboratory_id] += 1

    nodes = [{"id": "root", "label": "Competencias de IA", "type": "root", "status": "overview"}]
    edges = []
    seen_topics = set()
    for lab in labs:
        lab_node = f"lab-{lab.id}"
        grades = lab_scores[lab.id]
        nodes.append({"id": lab_node, "label": lab.name, "type": "laboratory", "cohort": lab.cohort,
                      "grade": _avg(grades), "approved_evaluations": len(grades),
                      "evidence_count": evidence_count[lab.id]})
        edges.append({"from": "root", "to": lab_node, "type": "includes"})
        for topic in map(str, lab.topics or []):
            topic_node = f"topic-{topic}"
            if topic not in seen_topics:
                seen_topics.add(topic)
                nodes.append({"id": topic_node, "label": topic.replace("_", " ").title(), "type": "topic",
                              "mastery": _avg(topic_scores[topic]), "laboratory_count": len(topic_labs[topic])})
                edges.append({"from": "root", "to": topic_node, "type": "competency"})
            edges.append({"from": lab_node, "to": topic_node, "type": "covers"})
    for evidence in evidences:
        evidence_node = f"evidence-{evidence.id}"
        nodes.append({"id": evidence_node, "label": evidence.original_name, "type": "evidence",
                      "student": evidence.student, "laboratory_id": evidence.laboratory_id,
                      "download_url": f"/api/evidence/{evidence.id}/download"})
        edges.append({"from": f"lab-{evidence.laboratory_id}", "to": evidence_node, "type": "evidence"})
    return {"nodes": nodes, "edges": edges, "filters": {"cohort": cohort, "student": student}}
