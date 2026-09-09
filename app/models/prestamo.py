"""Préstamo: crédito interno con ciclo de vida explícito (FR-005, FR-006)."""

from __future__ import annotations

from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models import Base

PENDIENTE = "Pendiente"
APROBADO = "Aprobado"
RECHAZADO = "Rechazado"
ACTIVO = "Activo"
EN_MORA = "En mora"
PAGADO = "Pagado"
CERRADO = "Cerrado"


class Prestamo(Base):
    __tablename__ = "prestamos"

    id = Column(Integer, primary_key=True)
    solicitante_id = Column(Integer, ForeignKey("ahorradores.id"), nullable=False, index=True)
    monto = Column(Integer, nullable=False)  # COP enteros, > 0
    plazo_meses = Column(Integer, nullable=False)
    motivo = Column(String(280), nullable=False)
    tasa_mensual_aplicada = Column(Float, nullable=False)  # snapshot del parámetro
    estado = Column(String(20), nullable=False, default=PENDIENTE, index=True)
    aprobado_por = Column(String(80), nullable=True)
    fecha_solicitud = Column(Date, nullable=False)
    fecha_aprobacion = Column(Date, nullable=True)

    cuotas = relationship("Cuota", back_populates="prestamo", cascade="all, delete-orphan")
