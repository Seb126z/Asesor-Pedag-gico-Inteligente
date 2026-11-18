"""Construcción de resultados de evaluación a partir de la rúbrica oficial.

Las funciones son puras (no tocan la base de datos ni HTTP): las rutas solo traducen
`InvalidResult` a un error 422. La nota la calcula siempre `calculate_grade`.
"""
from app.core.clock import utcnow
from app.services.rubrics import calculate_grade, same_name, score_level

FALLBACK_MODEL = "respaldo-sin-llm"


class InvalidResult(ValueError):
    """El resultado enviado no corresponde a la rúbrica vigente."""


def grade_manual_result(rubric: list[dict], criteria_results) -> float:
    """Valida los resultados enviados por el cliente (mismo orden que la rúbrica) y calcula la nota."""
    if not isinstance(criteria_results, list) or len(criteria_results) != len(rubric):
        raise InvalidResult("La cantidad de resultados no coincide con los criterios de la rúbrica oficial")
    normalized = []
    for rubric_item, result_item in zip(rubric, criteria_results):
        if not isinstance(result_item, dict):
            raise InvalidResult("Cada resultado de criterio debe ser un objeto")
        name = result_item.get("criterio")
        if name is not None and not same_name(name, rubric_item["name"]):
            raise InvalidResult("El nombre/orden de los criterios no coincide con la rúbrica vigente")
        try:
            score = float(result_item.get("score"))
        except (TypeError, ValueError):
            raise InvalidResult("Cada criterio necesita una puntuación numérica") from None
        if not 0 <= score <= 5:
            raise InvalidResult("Cada puntuación debe estar entre 0 y 5")
        normalized.append({"score": score, "weight": float(rubric_item["weight"])})
    return calculate_grade(normalized)


def build_ai_result(lab, ai: dict, evidence_name: str, extracted: bool, model_name: str) -> dict:
    """Empareja la respuesta del LLM con la rúbrica por nombre de criterio y calcula la nota.

    Un criterio que el modelo no evaluó recibe 0 y se marca como brecha.
    """
    fallback = bool(ai.get("fallback"))
    by_name = {str(c.get("name", "")).strip().casefold(): c for c in ai.get("crit", [])}
    crit, normalized = [], []
    for rubric_item in lab.rubric:
        found = by_name.get(rubric_item["name"].strip().casefold())
        score = max(0.0, min(5.0, float(found["score"]))) if found else 0.0
        crit.append({"criterio": rubric_item["name"], "peso": rubric_item["weight"], "score": score,
                     "nivel": score_level(score),
                     "evidencia": found.get("justification") if found else "El modelo no evaluó este criterio.",
                     "fortaleza": None, "brecha": None if found else "Criterio sin evaluar"})
        normalized.append({"score": score, "weight": float(rubric_item["weight"])})

    return {"laboratorio": lab.name, "version_rubrica": lab.rubric_version,
            "modelo": FALLBACK_MODEL if fallback else model_name,
            "fecha": utcnow().date().isoformat(), "summary": ai.get("summary"),
            "fallback_reason": ai.get("fallback_reason"),
            "strengths": ai.get("strengths", []), "weaknesses": ai.get("weaknesses", []),
            "verificacion": {"texto_extraido": extracted, "evidencia": evidence_name,
                             "sandbox": "no ejecutado en este prototipo"},
            "crit": crit, "preliminary_grade": calculate_grade(normalized), "fallback": fallback}
