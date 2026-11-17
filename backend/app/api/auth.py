from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import DUMMY_HASH, create_token, hash_password, verify_password
from app.models.entities import User
from app.schemas.contracts import RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token_response(user: User) -> TokenOut:
    return TokenOut(access_token=create_token(user.id, user.role), user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenOut, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    """Registro público: siempre crea una cuenta de estudiante. Los docentes los crea el administrador."""
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Ya existe una cuenta con ese correo")
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password), role="estudiante")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ya existe una cuenta con ese correo")
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Recibe `username` (el correo) y `password` como formulario, para que el botón Authorize de /docs funcione."""
    user = db.query(User).filter(User.email == form.username.strip().lower()).first()
    password_ok = verify_password(form.password, user.password_hash if user else DUMMY_HASH)
    if not user or not password_ok or not user.active:
        raise HTTPException(401, "Correo o contraseña incorrectos", headers={"WWW-Authenticate": "Bearer"})
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
