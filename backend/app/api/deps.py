"""Dependencias de FastAPI: usuario actual y control de roles."""
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.entities import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


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
