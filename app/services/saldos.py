"""Saldos derivados: única fuente para saldos y fondo total (principio I)."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.aporte import Aporte
from app.models.prestamo import Prestamo


def saldo_acumulado(db: Session, ahorrador_id: int) -> int:
    return (
        db.query(func.coalesce(func.sum(Aporte.monto), 0))
        .filter_by(ahorrador_id=ahorrador_id)
        .scalar()
        or 0
    )


def fondo_total(db: Session) -> int:
    return db.query(func.coalesce(func.sum(Aporte.monto), 0)).scalar() or 0


def prestado_activo(db: Session) -> int:
    """Capital desembolsado pendiente (Aprobado/Activo/En mora)."""
    from app.services.mora import ESTADOS_VIGENTES

    return (
        db.query(func.coalesce(func.sum(Prestamo.monto), 0))
        .filter(Prestamo.estado.in_(ESTADOS_VIGENTES))
        .scalar()
        or 0
    )


def fondo_disponible(db: Session) -> int:
    """Fondo prestable = aportado menos capital pendiente."""
    return fondo_total(db) - prestado_activo(db)


def historial(db: Session, ahorrador_id: int) -> list[Aporte]:
    return (
        db.query(Aporte)
        .filter_by(ahorrador_id=ahorrador_id)
        .order_by(Aporte.fecha.asc(), Aporte.id.asc())
        .all()
    )
