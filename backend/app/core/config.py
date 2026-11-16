import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR.parent / ".env")

APP_NAME = os.getenv("APP_NAME", "Asesor Pedagógico Inteligente")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./storage/asesor_pedagogico.db")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(ROOT_DIR / "storage" / "evidencias")))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
