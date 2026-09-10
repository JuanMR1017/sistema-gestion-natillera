"""Notificación: aviso automático al destinatario (FR-010, HU-10).

Tipos: solicitud_recibida | cambio_estado | vencimiento | recordatorio_aporte.
Canal base: plataforma; correo como complemento configurable (US6).
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.models import Base

SOLICITUD_RECIBIDA = "solicitud_recibida"
CAMBIO_ESTADO = "cambio_estado"
VENCIMIENTO = "vencimiento"
RECORDATORIO_APORTE = "recordatorio_aporte"

CANAL_PLATAFORMA = "plataforma"
CANAL_CORREO = "correo"


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True)
    destinatario = Column(String(80), nullable=False, index=True)  # username
    tipo = Column(String(30), nullable=False, index=True)
    canal = Column(String(20), nullable=False, default=CANAL_PLATAFORMA)
    detalle = Column(String(500), nullable=False)
    leida = Column(Boolean, nullable=False, default=False)
    creada_en = Column(DateTime, nullable=False, server_default=func.now())
