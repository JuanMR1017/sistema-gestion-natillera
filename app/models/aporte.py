"""Aporte: movimiento de ahorro inmutable, append-only (FR-003)."""

from __future__ import annotations

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models import Base


class Aporte(Base):
    __tablename__ = "aportes"

    id = Column(Integer, primary_key=True)
    ahorrador_id = Column(Integer, ForeignKey("ahorradores.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False)
    monto = Column(Integer, nullable=False)  # COP enteros, > 0
    comprobante = Column(String(120), nullable=False)
    registrado_por = Column(String(80), nullable=False)
    registrado_en = Column(DateTime, nullable=False, server_default=func.now())

    ahorrador = relationship("Ahorrador", back_populates="aportes")
