"""Contraseñas (PBKDF2 de la librería estándar) y tokens JWT (PyJWT)."""
import base64
import hashlib
import hmac
import os
import time

import jwt

from app.core.config import JWT_SECRET, JWT_EXPIRE_MINUTES

_ITERATIONS = 600_000
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        _ITERATIONS, base64.b64encode(salt).decode(), base64.b64encode(digest).decode()
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_b64, digest_b64 = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        expected = base64.b64decode(digest_b64)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), base64.b64decode(salt_b64), int(iterations), dklen=len(expected)
        )
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


# Hash de relleno: se verifica cuando el correo no existe, para que el tiempo de respuesta no delate si la cuenta existe.
DUMMY_HASH = hash_password("relleno-no-valido")


def create_token(user_id: int, role: str) -> str:
    now = int(time.time())
    payload = {"sub": str(user_id), "role": role, "iat": now, "exp": now + JWT_EXPIRE_MINUTES * 60}
    return jwt.encode(payload, JWT_SECRET, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """Lanza jwt.PyJWTError si el token es inválido o venció."""
    return jwt.decode(token, JWT_SECRET, algorithms=[_ALGORITHM], options={"require": ["exp", "sub"]})
