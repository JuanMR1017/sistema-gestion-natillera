"""Cuenta de acceso al sistema (FR-001)."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.models import Base

ROL_AHORRADOR = "Ahorrador"
ROL_ADMINISTRADOR = "Administrador"
ROLES_VALIDOS = (ROL_AHORRADOR, ROL_ADMINISTRADOR)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(120), nullable=False)
    rol = Column(String(20), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, nullable=False, server_default=func.now())
