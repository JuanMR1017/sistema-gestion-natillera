"""Reparto anual: liquidación de diciembre auditable (FR-011, RN-05)."""

from __future__ import annotations

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models import Base


class Reparto(Base):
    __tablename__ = "repartos"

    id = Column(Integer, primary_key=True)
    ciclo_ano = Column(Integer, nullable=False, unique=True, index=True)
    fecha_corte = Column(Date, nullable=False)
    fecha_ejecucion = Column(DateTime, nullable=False, server_default=func.now())
    ejecutado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    total_fondo = Column(Integer, nullable=False)
    total_utilidades = Column(Integer, nullable=False)

    lineas = relationship("RepartoLinea", back_populates="reparto",
                          cascade="all, delete-orphan")


class RepartoLinea(Base):
    __tablename__ = "reparto_lineas"

    id = Column(Integer, primary_key=True)
    reparto_id = Column(Integer, ForeignKey("repartos.id"), nullable=False, index=True)
    ahorrador_id = Column(Integer, ForeignKey("ahorradores.id"), nullable=False)
    ahorro_aportado = Column(Integer, nullable=False)
    utilidad_proporcional = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)

    reparto = relationship("Reparto", back_populates="lineas")
