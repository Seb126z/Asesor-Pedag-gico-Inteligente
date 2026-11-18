from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.routes import router as api_router
from app.core.config import APP_NAME, UPLOAD_DIR
from app.core.database import SessionLocal, ensure_schema
from app.services.seed import seed_laboratories
from app.services.users import seed_users

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_schema()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        seed_laboratories(db)
        seed_users(db)
    yield


app = FastAPI(title=APP_NAME, version="0.2.0", lifespan=lifespan,
              description="API para gestión de evidencias, rúbricas y evaluaciones.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)
app.include_router(api_router)
# Se monta al final para que /api/* tenga prioridad sobre los archivos estáticos.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
