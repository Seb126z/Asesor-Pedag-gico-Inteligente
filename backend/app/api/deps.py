"""Dependencias de FastAPI: usuario actual, control de roles y utilidades comunes de las rutas."""
from typing import TypeVar

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.entities import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
T = TypeVar("T")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    invalid = HTTPException(401, "Sesión inválida o vencida", headers={"WWW-Authenticate": "Bearer"})
    try:
        user_id = int(decode_token(token)["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise invalid
    user = db.get(User, user_id)
    if not user or not user.active:
        raise invalid
    return user


def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "No tienes permiso para esta acción")
        return user
    return checker


require_docente = require_role("docente")


def is_docente(user: User) -> bool:
    return user.role == "docente"


def student_scope(user: User) -> int | None:
    """Los estudiantes solo ven lo suyo (filtro por id de usuario); el docente ve todo (None)."""
    return None if is_docente(user) else user.id


def get_or_404(db: Session, model: type[T], item_id: int, message: str) -> T:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(404, message)
    return item
