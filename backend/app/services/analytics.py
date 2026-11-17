from collections import defaultdict
from statistics import mean

from app.models.entities import Evaluation, Evidence, Laboratory


def build_analytics_report(db, cohort: int | None = None, student: str | None = None, student_id: int | None = None):
    labs_query = db.query(Laboratory)
    if cohort is not None:
        labs_query = labs_query.filter(Laboratory.cohort == cohort)
    labs = labs_query.order_by(Laboratory.cohort, Laboratory.id).all()
    lab_ids = {lab.id for lab in labs}

    evaluations_query = db.query(Evaluation).filter(Evaluation.laboratory_id.in_(lab_ids)) if lab_ids else db.query(Evaluation).filter(Evaluation.id == -1)
    if student:
        evaluations_query = evaluations_query.filter(Evaluation.student == student)
    if student_id is not None:
        evaluations_query = evaluations_query.filter(Evaluation.student_id == student_id)
    evaluations = evaluations_query.order_by(Evaluation.created_at.asc()).all()
    approved = [ev for ev in evaluations if ev.approved and ev.final_grade is not None]

    evidence_query = db.query(Evidence).filter(Evidence.laboratory_id.in_(lab_ids)) if lab_ids else db.query(Evidence).filter(Evidence.id == -1)
    if student:
        evidence_query = evidence_query.filter(Evidence.student == student)
    if student_id is not None:
        evidence_query = evidence_query.filter(Evidence.student_id == student_id)
    evidences = evidence_query.all()

    approved_by_lab = defaultdict(list)
    for ev in approved:
        approved_by_lab[ev.laboratory_id].append(ev)

    lab_rows = []
    criterion_scores = defaultdict(list)
    for lab in labs:
        lab_evals = approved_by_lab[lab.id]
        grades = [float(ev.final_grade) for ev in lab_evals]
        for ev in lab_evals:
            for item in (ev.result or {}).get("crit", []):
                name = str(item.get("criterio", "")).strip()
                if name and item.get("score") is not None:
                    criterion_scores[(lab.id, name)].append(float(item["score"]))
        lab_rows.append({
            "laboratory_id": lab.id,
            "laboratory": lab.name,
            "cohort": lab.cohort,
            "topics": lab.topics or [],
            "evaluations": len(lab_evals),
            "evidence_count": sum(1 for ev in evidences if ev.laboratory_id == lab.id),
            "average_grade": round(mean(grades), 2) if grades else None,
        })

    gaps = []
    strengths = []
    for (lab_id, criterion), scores in criterion_scores.items():
        avg = round(mean(scores), 2)
        lab = next((item for item in labs if item.id == lab_id), None)
        item = {"laboratory_id": lab_id, "laboratory": lab.name if lab else "", "criterion": criterion,
                "average_score": avg, "sample_size": len(scores)}
        (gaps if avg < 3.5 else strengths).append(item)

    cohort_rows = []
    for cohort_id in sorted({lab.cohort for lab in labs}):
        cohort_lab_ids = {lab.id for lab in labs if lab.cohort == cohort_id}
        cohort_evals = [ev for ev in approved if ev.laboratory_id in cohort_lab_ids]
        grades = [float(ev.final_grade) for ev in cohort_evals]
        cohort_rows.append({"cohort": cohort_id, "laboratories": len(cohort_lab_ids),
                            "approved_evaluations": len(cohort_evals),
                            "average_grade": round(mean(grades), 2) if grades else None})

    all_grades = [float(ev.final_grade) for ev in approved]
    return {
        "filters": {"cohort": cohort, "student": student},
        "totals": {"laboratories": len(labs), "evaluations": len(evaluations),
                   "approved_evaluations": len(approved), "evidences": len(evidences),
                   "average_grade": round(mean(all_grades), 2) if all_grades else None},
        "cohorts": cohort_rows,
        "laboratories": lab_rows,
        "strengths": sorted(strengths, key=lambda x: x["average_score"], reverse=True),
        "gaps": sorted(gaps, key=lambda x: x["average_score"]),
        "recommendations": [
            {**gap, "recommendation": f"Reforzar {gap['criterion'].lower()} mediante ejercicios guiados y una nueva evidencia para {gap['laboratory']}."}
            for gap in sorted(gaps, key=lambda x: x["average_score"])
        ],
    }


def build_mindmap(db, cohort: int | None = None, student: str | None = None, student_id: int | None = None):
    labs_query = db.query(Laboratory)
    if cohort is not None:
        labs_query = labs_query.filter(Laboratory.cohort == cohort)
    labs = labs_query.order_by(Laboratory.cohort, Laboratory.id).all()
    lab_ids = {lab.id for lab in labs}
    eval_query = db.query(Evaluation).filter(Evaluation.laboratory_id.in_(lab_ids), Evaluation.approved.is_(True)) if lab_ids else db.query(Evaluation).filter(Evaluation.id == -1)
    if student:
        eval_query = eval_query.filter(Evaluation.student == student)
    if student_id is not None:
        eval_query = eval_query.filter(Evaluation.student_id == student_id)
    evaluations = [ev for ev in eval_query.all() if ev.final_grade is not None]
    evidence_query = db.query(Evidence).filter(Evidence.laboratory_id.in_(lab_ids)) if lab_ids else db.query(Evidence).filter(Evidence.id == -1)
    if student:
        evidence_query = evidence_query.filter(Evidence.student == student)
    if student_id is not None:
        evidence_query = evidence_query.filter(Evidence.student_id == student_id)
    evidences = evidence_query.all()

    topic_labs = defaultdict(set)
    topic_scores = defaultdict(list)
    lab_scores = defaultdict(list)
    for lab in labs:
        for topic in lab.topics or []:
            topic_labs[str(topic)].add(lab.id)
    for ev in evaluations:
        lab_scores[ev.laboratory_id].append(float(ev.final_grade))
        for topic in next((l.topics or [] for l in labs if l.id == ev.laboratory_id), []):
            topic_scores[str(topic)].append(float(ev.final_grade))

    nodes = [{"id": "root", "label": "Competencias de IA", "type": "root", "status": "overview"}]
    edges = []
    seen_topics = set()
    for lab in labs:
        lab_node = f"lab-{lab.id}"
        grades = lab_scores[lab.id]
        nodes.append({"id": lab_node, "label": lab.name, "type": "laboratory", "cohort": lab.cohort,
                      "grade": round(mean(grades), 2) if grades else None,
                      "approved_evaluations": len(grades), "evidence_count": sum(1 for e in evidences if e.laboratory_id == lab.id)})
        edges.append({"from": "root", "to": lab_node, "type": "includes"})
        for topic in lab.topics or []:
            topic = str(topic)
            topic_node = f"topic-{topic}"
            if topic not in seen_topics:
                scores = topic_scores[topic]
                nodes.append({"id": topic_node, "label": topic.replace("_", " ").title(), "type": "topic",
                              "mastery": round(mean(scores), 2) if scores else None,
                              "laboratory_count": len(topic_labs[topic])})
                edges.append({"from": "root", "to": topic_node, "type": "competency"})
                seen_topics.add(topic)
            edges.append({"from": lab_node, "to": topic_node, "type": "covers"})
    for evidence in evidences:
        evidence_node = f"evidence-{evidence.id}"
        nodes.append({"id": evidence_node, "label": evidence.original_name, "type": "evidence",
                      "student": evidence.student, "laboratory_id": evidence.laboratory_id,
                      "download_url": f"/api/evidence/{evidence.id}/download"})
        edges.append({"from": f"lab-{evidence.laboratory_id}", "to": evidence_node, "type": "evidence"})
    return {"nodes": nodes, "edges": edges, "filters": {"cohort": cohort, "student": student}}
