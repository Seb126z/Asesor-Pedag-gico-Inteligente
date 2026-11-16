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
