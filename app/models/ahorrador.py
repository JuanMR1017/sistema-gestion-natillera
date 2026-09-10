"""Ahorrador: participante del fondo con saldo siempre derivado (FR-002)."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models import Base


class Ahorrador(Base):
    __tablename__ = "ahorradores"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, unique=True)
    nombre = Column(String(120), nullable=False)
    documento = Column(String(40), nullable=False, unique=True, index=True)
    area = Column(String(80), nullable=False)
    fecha_ingreso = Column(Date, nullable=False)
    activo = Column(Boolean, nullable=False, default=True)

    usuario = relationship("Usuario", uselist=False)
    aportes = relationship("Aporte", back_populates="ahorrador",
                           cascade="all, delete-orphan")

    def saldo(self, db=None) -> int:
        """Saldo derivado de aportes registrados; nunca se edita a mano."""
        if db is None:
            return 0
        from app.services.saldos import saldo_acumulado

        return saldo_acumulado(db, self.id)
