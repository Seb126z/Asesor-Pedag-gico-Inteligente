import os
from pathlib import Path
from urllib.parse import quote, unquote
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]   # .../backend
ROOT_DIR = BACKEND_DIR                               # se conserva el nombre usado antes
load_dotenv(BACKEND_DIR.parent / ".env")


def _resolve_path(value: str) -> Path:
    """Las rutas relativas se interpretan desde backend/, no desde donde se lance el comando."""
    path = Path(value)
    return path if path.is_absolute() else (BACKEND_DIR / path).resolve()


def _resolve_database_url(url: str) -> str:
    url = url.strip().strip("\"'").strip()  # espacios o comillas pegados por error al copiar el valor
    # Supabase/Render entregan "postgres://" o "postgresql://"; se fija el driver psycopg2 (el de requirements)
    for prefix in ("postgres://", "postgresql://", "postgresql+psycopg2://"):
        if url.startswith(prefix):
            rest = url[len(prefix):]
            creds, at, hostpart = rest.rpartition("@")  # la ÚLTIMA @ separa credenciales de servidor
            if at:
                user, colon, password = creds.partition(":")
                if colon:  # codifica caracteres especiales de la contraseña (@ # / : ...) sin doble codificar
                    password = quote(unquote(password), safe="")
                creds = user + colon + password
                rest = creds + "@" + hostpart
            return "postgresql+psycopg2://" + rest
    prefix = "sqlite:///"
    if url.startswith(prefix) and not url.startswith("sqlite:////") and url != "sqlite://":
        raw = url[len(prefix):]
        if raw and not Path(raw).is_absolute() and ":" not in raw[:3]:
            return prefix + _resolve_path(raw).as_posix()
    return url


APP_NAME = os.getenv("APP_NAME", "Asesor Pedagógico Inteligente")
DATABASE_URL = _resolve_database_url(os.getenv("DATABASE_URL", "sqlite:///./storage/asesor_pedagogico.db"))
UPLOAD_DIR = _resolve_path(os.getenv("UPLOAD_DIR", "./storage/evidencias"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
ALLOWED_EXTENSIONS = frozenset({".pdf", ".zip", ".txt", ".py", ".js", ".html", ".docx",
                                ".pptx", ".png", ".jpg", ".jpeg", ".mp4"})

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
