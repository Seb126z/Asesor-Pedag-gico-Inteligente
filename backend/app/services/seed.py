"""Datos iniciales: los seis laboratorios del curso con su rúbrica v1.0."""
from sqlalchemy.orm import Session

from app.models.entities import Laboratory


def _rubric(*criteria: tuple[str, int, list[str]]) -> list[dict]:
    return [{"name": name, "weight": weight, "indicators": indicators} for name, weight, indicators in criteria]


LABORATORIES = [
    (1, 1, "Lab 1 · Búsqueda y agentes", ["busqueda", "agentes"], _rubric(
        ("Algoritmo de búsqueda", 40, ["bfs", "a*", "heurística", "nodos"]),
        ("Diseño del agente", 30, ["agente", "percepción", "acción", "entorno"]),
        ("Análisis de resultados", 30, ["complejidad", "comparación", "tiempo"]))),
    (2, 1, "Lab 2 · Aprendizaje supervisado", ["supervisado"], _rubric(
        ("Preparación de datos", 30, ["normalización", "partición", "limpieza"]),
        ("Modelo y entrenamiento", 40, ["regresión", "árbol", "entrenamiento", "hiperparámetros"]),
        ("Evaluación", 30, ["accuracy", "f1", "validación cruzada"]))),
    (3, 1, "Lab 3 · Redes neuronales", ["redes"], _rubric(
        ("Arquitectura", 40, ["capas", "activación", "neuronas"]),
        ("Entrenamiento", 35, ["backpropagation", "épocas", "optimizador", "pérdida"]),
        ("Regularización", 25, ["dropout", "overfitting"]))),
    (4, 2, "Lab 4 · Procesamiento de lenguaje", ["nlp"], _rubric(
        ("Preprocesamiento", 35, ["tokenización", "stopwords", "lematización"]),
        ("Representación", 35, ["tf-idf", "embeddings"]),
        ("Clasificación", 30, ["sentimiento", "clasificador", "f1"]))),
    (5, 2, "Lab 5 · Visión artificial", ["vision"], _rubric(
        ("Datos de imágenes", 30, ["aumentación", "etiquetas", "resolución"]),
        ("Modelo CNN", 40, ["convolución", "pooling", "cnn"]),
        ("Métricas", 30, ["precisión", "matriz de confusión"]))),
    (6, 2, "Lab 6 · LLM y RAG", ["llm", "nlp"], _rubric(
        ("Recuperación", 35, ["embeddings", "vectorial", "chunks"]),
        ("Prompting", 35, ["prompt", "contexto", "json"]),
        ("Evaluación y alucinaciones", 30, ["alucinación", "citas", "verificación"]))),
]

DEFAULT_DESCRIPTION = "Descripción y objetivos por completar con la guía oficial del laboratorio."


def seed_laboratories(db: Session) -> None:
    """Crea los laboratorios solo si la tabla está vacía (no sobrescribe rúbricas editadas)."""
    if db.query(Laboratory).count():
        return
    for lab_id, cohort, name, topics, rubric in LABORATORIES:
        db.add(Laboratory(id=lab_id, cohort=cohort, name=name, topics=topics, rubric_version="1.0",
                          rubric=rubric, description=DEFAULT_DESCRIPTION))
    db.commit()
