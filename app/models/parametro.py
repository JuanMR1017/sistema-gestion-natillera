"""Parámetros versionados del fondo (FR-012): tasa, tope, mínimo, gracia.

Nunca se editan destructivamente: cada cambio cierra la vigencia anterior y abre
una nueva. Los préstamos conservan snapshot de la tasa aplicada.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Column, Date, Integer, String
from sqlalchemy.orm import Session

from app.models import Base

TASA_MENSUAL = "tasa_mensual"
TOPE_PORCENTAJE_SALDO = "tope_porcentaje_saldo"
MONTO_MINIMO_APORTE = "monto_minimo_aporte"
DIAS_GRACIA_MORA = "dias_gracia_mora"

DEFAULTS: dict[str, str] = {
    TASA_MENSUAL: "0.015",
    TOPE_PORCENTAJE_SALDO: "80",
    MONTO_MINIMO_APORTE: "0",
    DIAS_GRACIA_MORA: "5",
}


class Parametro(Base):
    __tablename__ = "parametros"

    id = Column(Integer, primary_key=True)
    clave = Column(String(60), nullable=False, index=True)
    valor = Column(String(60), nullable=False)
    vigente_desde = Column(Date, nullable=False)
    vigente_hasta = Column(Date, nullable=True)  # null = actual
    modificado_por = Column(String(80), nullable=True)


def vigente(db: Session, clave: str, default: str | None = None) -> str:
    row = (
        db.query(Parametro)
        .filter_by(clave=clave, vigente_hasta=None)
        .order_by(Parametro.vigente_desde.desc())
        .first()
    )
    if row is not None:
        return row.valor
    if default is not None:
        return default
    return DEFAULTS[clave]


def seed_defaults(db: Session, hoy: date, autor: str = "seed") -> None:
    for clave, valor in DEFAULTS.items():
        existe = db.query(Parametro).filter_by(clave=clave, vigente_hasta=None).first()
        if existe is None:
            db.add(
                Parametro(
                    clave=clave, valor=valor, vigente_desde=hoy, vigente_hasta=None,
                    modificado_por=autor,
                )
            )
    db.commit()
