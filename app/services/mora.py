"""Mora automática por días de gracia parametrizados (RN-04, FR-005).

Regla: una cuota no pagada pasa a mora al superar los días de gracia
tras su vencimiento (por defecto 5, parámetro `dias_gracia_mora`).
La evaluación es on-read: se ejecuta en cada ruta que decide sobre
mora (solicitud, pagos, cartera) además de cualquier job programado.
El bloqueo RN-04 se levanta solo al registrarse el pago que pone al día.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.models.cuota import Cuota
from app.models.parametro import DIAS_GRACIA_MORA, vigente
from app.models.prestamo import EN_MORA, Prestamo

# Estados con capital desembolsado pendiente (cuentan para liquidez y mora).
ESTADOS_VIGENTES = ("Aprobado", "Activo", "En mora")


def dias_gracia(db: Session) -> int:
    return int(vigente(db, DIAS_GRACIA_MORA))


def dias_vencidos(fecha_vencimiento: date, hoy: date) -> int:
    return (hoy - fecha_vencimiento).days


def cuota_en_mora(cuota: Cuota, hoy: date, gracia: int) -> bool:
    return cuota.estado != "Pagada" and dias_vencidos(cuota.fecha_vencimiento, hoy) > gracia


def evaluar_mora(db: Session, hoy: date | None = None) -> dict[str, int]:
    """Marca cuotas vencidas como En mora y propaga a sus préstamos.

    Retorna conteos para auditoría.     Hace commit solo si hubo cambios.
    """
    hoy = hoy or datetime.now(UTC).date()
    gracia = dias_gracia(db)
    cuotas_marcadas = 0
    for c in db.query(Cuota).filter(Cuota.estado.in_(["Pendiente", "Parcial"])).all():
        if cuota_en_mora(c, hoy, gracia):
            c.estado = "En mora"
            cuotas_marcadas += 1
    prestamos_marcados = 0
    for p in db.query(Prestamo).filter(Prestamo.estado.in_(ESTADOS_VIGENTES)).all():
        en_mora = any(c.estado == "En mora" for c in p.cuotas)
        if en_mora and p.estado != EN_MORA:
            p.estado = EN_MORA
            prestamos_marcados += 1
        elif not en_mora and p.estado == EN_MORA and p.cuotas:
            # Al día de nuevo: vuelve a cartera activa (el bloqueo se levanta
            # solo vía pagos registrados, nunca a mano).
            p.estado = "Activo"
    if cuotas_marcadas or prestamos_marcados:
        db.commit()
    return {"cuotas": cuotas_marcadas, "prestamos": prestamos_marcados}


def ahorrador_en_mora(db: Session, ahorrador_id: int, hoy: date | None = None) -> bool:
    """True si el ahorrador tiene alguna cuota en mora (RN-04)."""
    hoy = hoy or datetime.now(UTC).date()
    evaluar_mora(db, hoy)
    ids = [
        p.id for p in
        db.query(Prestamo).filter_by(solicitante_id=ahorrador_id)
        .filter(Prestamo.estado.in_(ESTADOS_VIGENTES)).all()
    ]
    if not ids:
        return False
    return (
        db.query(Cuota)
        .filter(Cuota.prestamo_id.in_(ids), Cuota.estado == "En mora")
        .count()
        > 0
    )


def saldo_pendiente(prestamo: Prestamo) -> int:
    """Capital+interés aún no abonado del préstamo (derivado, FR-008)."""
    return sum(c.valor - c.abonado for c in prestamo.cuotas)
