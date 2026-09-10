"""Carga: 200+ ahorradores con consultas dentro de umbrales (T054, SC-011)."""

import time
from datetime import date


def test_carga_200_ahorradores_consultas_menos_3s(db):
    from app.models.ahorrador import Ahorrador
    from app.models.aporte import Aporte
    from app.services import reportes
    from app.services.saldos import fondo_disponible, fondo_total, saldo_acumulado

    base = date(2026, 1, 5)
    for i in range(220):
        a = Ahorrador(nombre=f"Carga {i}", documento=f"C{i:04d}", area="TI",
                      fecha_ingreso=base)
        db.add(a)
        db.flush()
        for j in range(2):
            db.add(Aporte(ahorrador_id=a.id, fecha=date(2026, 2 + j, 1),
                          monto=100000, comprobante=f"C{i}-{j}",
                          registrado_por="admin"))
    db.commit()
    assert fondo_total(db) == 220 * 2 * 100000

    t0 = time.perf_counter()
    assert saldo_acumulado(db, 1) == 200000
    assert fondo_disponible(db) == 220 * 2 * 100000
    t_consultas = time.perf_counter() - t0

    t0 = time.perf_counter()
    rep = reportes.reporte_aportes(db, date(2026, 1, 1), date(2026, 12, 31))
    assert rep["total"] == 220 * 2 * 100000
    assert len(rep["filas"]) == 440
    xlsx = reportes.a_excel("aportes", rep)
    assert len(xlsx) > 1000
    t_reportes = time.perf_counter() - t0

    assert t_consultas < 3, f"consultas {t_consultas:.2f}s"
    assert t_reportes < 3, f"reportes {t_reportes:.2f}s"
