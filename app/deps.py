"""Infraestructura compartida: settings, base de datos, contraseñas, sesiones y roles.

Deny-by-default: toda ruta exige sesión válida; cada rol solo accede a lo suyo.
Sin sesión → 401. Rol insuficiente → 403 (con auditoría).
Sesiones firmadas con expiración (12 h por defecto).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from itsdangerous import URLSafeTimedSerializer
from itsdangerous.exc import BadData, SignatureExpired
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger("natillera")

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./natillera.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
SESSION_COOKIE = "natillera_session"
# Sesión expira tras 12 h (T055: expiry). Ajustable por entorno.
SESSION_MAX_AGE = int(os.environ.get("SESSION_MAX_AGE", "43200"))

_engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


_signer = URLSafeTimedSerializer(SECRET_KEY, salt="natillera-session")


def create_session(username: str) -> str:
    return _signer.dumps({"sub": username})


def read_session(token: str | None, max_age: int = SESSION_MAX_AGE) -> str | None:
    if not token:
        return None
    try:
        data = _signer.loads(token, max_age=max_age)
    except (BadData, SignatureExpired):
        return None
    return data.get("sub") if isinstance(data, dict) else None


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Retorna el Usuario activo de la sesión o 401."""
    from app.models.usuario import Usuario  # import tardío: evita ciclo

    username = read_session(request.cookies.get(SESSION_COOKIE))
    user = (
        db.query(Usuario).filter_by(username=username, activo=True).first()
        if username
        else None
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    return user


def require_role(*roles: str):
    """Dependencia que exige uno de los roles o responde 403 (auditado)."""

    def _guard(request: Request, user=Depends(get_current_user)):
        if user.rol not in roles:
            logger.warning("403 denegado: usuario=%s rol=%s ruta=%s requiere=%s",
                           user.username, user.rol, request.url.path, roles)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
        return user

    return _guard
