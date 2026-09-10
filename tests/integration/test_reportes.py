"""Integración: reportes leen las mismas consultas que las vistas (T040).

Principio I: reporte y pantalla nunca divergen (única fuente).
"""

from datetime import date

from app.services import reportes
from app.services.saldos import fondo_disponible, fondo_total, prestado_activo


def _fondo(db):
    from app.models.ahorrador import Ahorrador
    from app.models.aporte import Aporte

    a = Ahorrador(nombre="Ana", documento="INT1", area="TI",
                  fecha_ingreso=date(2026, 1, 5))
    db.add(a)
    db.flush()
    db.add(Aporte(ahorrador_id=a.id, fecha=date(2026, 2, 1),
                  monto=150000, comprobante="T1", registrado_por="admin"))
    db.commit()
    return a


def test_totales_reportes_iguales_a_vistas(db):
    _fondo(db)
    rep_aportes = reportes.reporte_aportes(db, date(2026, 1, 1), date(2026, 12, 31))
    assert rep_aportes["total"] == fondo_total(db) == 150000
    fondos = reportes.reporte_fondos(db, date(2026, 12, 31))
    assert fondos["total_aportado"] == fondo_total(db)
    assert fondos["prestado_activo"] == prestado_activo(db)
    assert fondos["disponible"] == fondo_disponible(db)
    assert fondos["disponible"] == (fondos["total_aportado"]
                                    - fondos["prestado_activo"])
