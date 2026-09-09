"""Ejecución del cierre anual: ahorro + utilidad proporcional por integrante (HU-04)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.aporte import Aporte
from app.models.cuota import Cuota
from app.models.prestamo import CERRADO, PAGADO, Prestamo
from app.models.reparto import Reparto, RepartoLinea
from app.services.finance import interes_cobrado, reparto_proporcional


def ejecutar_reparto(db: Session, ciclo_ano: int, fecha_corte: date,
                     ejecutado_por: int) -> Reparto:
    if db.query(Reparto).filter_by(ciclo_ano=ciclo_ano).first():
        raise ValueError(f"El reparto del año {ciclo_ano} ya fue ejecutado.")

    filas = (
        db.query(Aporte.ahorrador_id, func.sum(Aporte.monto))
        .filter(Aporte.fecha <= fecha_corte)
        .group_by(Aporte.ahorrador_id)
        .all()
    )
    aportes = {ahorrador_id: total for ahorrador_id, total in filas}
    if not aportes:
        raise ValueError("No hay aportes para repartir al corte indicado.")

    # Interés cobrado por cuota (interés primero); suma exacta en Python.
    utilidades = sum(
        interes_cobrado(c.valor, c.interes, c.abonado)
        for c in db.query(Cuota).all()
    )

    partes = reparto_proporcional(aportes, utilidades)
    reparto = Reparto(
        ciclo_ano=ciclo_ano, fecha_corte=fecha_corte, ejecutado_por=ejecutado_por,
        total_fondo=sum(aportes.values()) + utilidades, total_utilidades=utilidades,
    )
    db.add(reparto)
    db.flush()
    for ahorrador_id, ahorro in aportes.items():
        u = partes[ahorrador_id]
        db.add(RepartoLinea(reparto_id=reparto.id, ahorrador_id=ahorrador_id,
                            ahorro_aportado=ahorro, utilidad_proporcional=u,
                            total=ahorro + u))
    # Préstamos totalmente pagados pasan a Cerrado/Archivado.
    for p in db.query(Prestamo).filter(Prestamo.estado.in_([PAGADO, "Activo"])).all():
        if p.cuotas and all(c.estado == "Pagada" for c in p.cuotas):
            p.estado = CERRADO
    db.commit()
    db.refresh(reparto)
    return reparto
