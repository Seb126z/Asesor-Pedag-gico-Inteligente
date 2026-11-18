"""Reglas de rúbricas: validación de ponderaciones, niveles y cálculo determinista de la nota."""


def validate_rubric(criteria: list[dict]) -> dict:
    total = round(sum(float(item.get("weight", 0)) for item in criteria), 4)
    names = [str(item.get("name", "")).strip().lower() for item in criteria]
    errors = []
    if not criteria:
        errors.append("La rúbrica debe tener al menos un criterio.")
    if abs(total - 100) > 0.0001:
        errors.append(f"Las ponderaciones suman {total:g}%; deben sumar 100%.")
    if any(not name for name in names):
        errors.append("Todos los criterios deben tener nombre.")
    if len(names) != len(set(names)):
        errors.append("Hay criterios con nombres duplicados.")
    return {"valid": not errors, "total_weight": total, "errors": errors}


def calculate_grade(criteria_results: list[dict]) -> float:
    """Cálculo determinista del backend; nunca delegar esta operación al LLM."""
    weighted = sum(float(item["score"]) * float(item["weight"]) / 100 for item in criteria_results)
    return round(max(0.0, min(5.0, weighted)), 2)


def score_level(score: float) -> str:
    """Nivel cualitativo de una puntuación de 0 a 5 (mismos cortes que el frontend)."""
    if score >= 4.5:
        return "Sobresaliente"
    if score >= 3.5:
        return "Alto"
    if score >= 2.5:
        return "Básico"
    return "Bajo" if score > 0 else "Sin evidencia"


def same_name(a, b) -> bool:
    """Compara nombres de criterio sin distinguir mayúsculas ni espacios de los extremos."""
    return str(a or "").strip().casefold() == str(b or "").strip().casefold()
