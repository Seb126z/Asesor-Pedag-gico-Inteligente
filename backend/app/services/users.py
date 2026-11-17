from sqlalchemy.orm import Session

from app.core.config import APP_ENV, DOCENTE_EMAIL, DOCENTE_NAME, DOCENTE_PASSWORD
from app.core.security import hash_password
from app.models.entities import User

DEMO_USERS = [
    ("Docente Demo", "docente@demo.local", "docente123", "docente"),
    ("Estudiante Demo", "estudiante@demo.local", "estudiante123", "estudiante"),
]


def _create(db: Session, name: str, email: str, password: str, role: str) -> None:
    if not db.query(User).filter(User.email == email.lower()).first():
        db.add(User(name=name, email=email.lower(), password_hash=hash_password(password), role=role))
        db.commit()


def seed_users(db: Session) -> None:
    """Desarrollo: crea cuentas demo. Producción: solo el docente definido en las variables de entorno."""
    if APP_ENV == "production":
        if DOCENTE_EMAIL and DOCENTE_PASSWORD:
            _create(db, DOCENTE_NAME, DOCENTE_EMAIL, DOCENTE_PASSWORD, "docente")
        return
    for name, email, password, role in DEMO_USERS:
        _create(db, name, email, password, role)
    print("Usuarios demo (solo desarrollo): docente@demo.local / docente123 · estudiante@demo.local / estudiante123")
