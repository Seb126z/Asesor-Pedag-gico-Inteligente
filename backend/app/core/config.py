import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR.parent / ".env")

APP_NAME = os.getenv("APP_NAME", "Asesor Pedagógico Inteligente")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./storage/asesor_pedagogico.db")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(ROOT_DIR / "storage" / "evidencias")))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))

# --- Seguridad y autenticación ---
APP_ENV = os.getenv("APP_ENV", "development")  # "production" en el servidor
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
DOCENTE_NAME = os.getenv("DOCENTE_NAME", "Docente")
DOCENTE_EMAIL = os.getenv("DOCENTE_EMAIL", "")
DOCENTE_PASSWORD = os.getenv("DOCENTE_PASSWORD", "")

if not JWT_SECRET:
    if APP_ENV == "production":
        raise RuntimeError("Falta JWT_SECRET: define una clave secreta larga en las variables de entorno.")
    JWT_SECRET = "desarrollo-local-no-usar-en-produccion-0123456789"
