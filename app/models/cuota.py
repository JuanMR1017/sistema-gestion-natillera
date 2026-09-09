"""Cuota: obligación periódica con desglose capital/interés del motor (FR-007)."""

from __future__ import annotations

from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models import Base


class Cuota(Base):
    __tablename__ = "cuotas"

    id = Column(Integer, primary_key=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=False, index=True)
    numero = Column(Integer, nullable=False)
    valor = Column(Integer, nullable=False)  # capital + interes, COP enteros
    capital = Column(Integer, nullable=False)
    interes = Column(Integer, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    abonado = Column(Integer, nullable=False, default=0)
    estado = Column(String(20), nullable=False, default="Pendiente", index=True)

    prestamo = relationship("Prestamo", back_populates="cuotas")
