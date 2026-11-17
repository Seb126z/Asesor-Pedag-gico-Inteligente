from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import APP_NAME, UPLOAD_DIR
from app.core.database import SessionLocal, ensure_schema
from app.models.entities import Laboratory
from app.api.routes import router
from app.api.auth import router as auth_router
from app.services.users import seed_users


SEED = [
 (1,1,"Lab 1 · Búsqueda y agentes",["busqueda","agentes"],[{"name":"Algoritmo de búsqueda","weight":40,"indicators":["bfs","a*","heurística","nodos"]},{"name":"Diseño del agente","weight":30,"indicators":["agente","percepción","acción","entorno"]},{"name":"Análisis de resultados","weight":30,"indicators":["complejidad","comparación","tiempo"]}]),
 (2,1,"Lab 2 · Aprendizaje supervisado",["supervisado"],[{"name":"Preparación de datos","weight":30,"indicators":["normalización","partición","limpieza"]},{"name":"Modelo y entrenamiento","weight":40,"indicators":["regresión","árbol","entrenamiento","hiperparámetros"]},{"name":"Evaluación","weight":30,"indicators":["accuracy","f1","validación cruzada"]}]),
 (3,1,"Lab 3 · Redes neuronales",["redes"],[{"name":"Arquitectura","weight":40,"indicators":["capas","activación","neuronas"]},{"name":"Entrenamiento","weight":35,"indicators":["backpropagation","épocas","optimizador","pérdida"]},{"name":"Regularización","weight":25,"indicators":["dropout","overfitting"]}]),
 (4,2,"Lab 4 · Procesamiento de lenguaje",["nlp"],[{"name":"Preprocesamiento","weight":35,"indicators":["tokenización","stopwords","lematización"]},{"name":"Representación","weight":35,"indicators":["tf-idf","embeddings"]},{"name":"Clasificación","weight":30,"indicators":["sentimiento","clasificador","f1"]}]),
 (5,2,"Lab 5 · Visión artificial",["vision"],[{"name":"Datos de imágenes","weight":30,"indicators":["aumentación","etiquetas","resolución"]},{"name":"Modelo CNN","weight":40,"indicators":["convolución","pooling","cnn"]},{"name":"Métricas","weight":30,"indicators":["precisión","matriz de confusión"]}]),
 (6,2,"Lab 6 · LLM y RAG",["llm","nlp"],[{"name":"Recuperación","weight":35,"indicators":["embeddings","vectorial","chunks"]},{"name":"Prompting","weight":35,"indicators":["prompt","contexto","json"]},{"name":"Evaluación y alucinaciones","weight":30,"indicators":["alucinación","citas","verificación"]}]),
]

@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_schema()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        if db.query(Laboratory).count() == 0:
            for lab_id, cohort, name, topics, rubric in SEED:
                db.add(Laboratory(id=lab_id, cohort=cohort, name=name, topics=topics, rubric_version="1.0", rubric=rubric, description="Descripción y objetivos por completar con la guía oficial del laboratorio."))
            db.commit()
        seed_users(db)
    yield


app = FastAPI(title=APP_NAME, version="0.1.0", description="API para gestión de evidencias, rúbricas y evaluaciones.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)
app.include_router(router)

frontend = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
