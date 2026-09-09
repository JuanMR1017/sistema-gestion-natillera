"""Unitarias del motor financiero: caso ancla del prototipo (T027)."""

from datetime import date

from app.services.finance import (
    cuota_francesa,
    imputar_pago,
    interes_cobrado,
    sumar_meses,
    tabla_cuotas,
)


def test_caso_ancla_prototipo_500k_12m():
    # Figma: $500.000 a 12 meses → $46.701/mes (tasa de referencia 1.8% m.v.)
    assert cuota_francesa(500000, 0.018, 12) == 46701


def test_tabla_cuotas_suma_capital_exacta():
    filas = tabla_cuotas(500000, 0.018, 12, date(2026, 1, 31))
    assert len(filas) == 12
    assert sum(f["capital"] for f in filas) == 500000
    assert all(f["valor"] == f["capital"] + f["interes"] for f in filas)
    assert all(f["valor"] > 0 for f in filas)
    assert filas[0]["fecha_vencimiento"] == date(2026, 2, 28)


def test_tasa_cero_reparte_capital():
    filas = tabla_cuotas(120000, 0.0, 4, date(2026, 1, 15))
    assert [f["valor"] for f in filas] == [30000, 30000, 30000, 30000]


def test_imputacion_pago_primero_interes():
    # Cuota 100000 = 90000 capital + 10000 interés; abono 40000 → todo a interés parcial
    a_interes, a_capital, nuevo, estado = imputar_pago(100000, 90000, 10000, 0, 40000)
    assert (a_interes, a_capital, nuevo, estado) == (10000, 30000, 40000, "Parcial")
    a_interes, a_capital, nuevo, estado = imputar_pago(100000, 90000, 10000, 40000, 60000)
    assert (a_interes, a_capital, nuevo, estado) == (0, 60000, 100000, "Pagada")
    assert interes_cobrado(100000, 10000, 40000) == 10000
    assert interes_cobrado(100000, 10000, 0) == 0


def test_sumar_meses_ajusta_fin_de_mes():
    assert sumar_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert sumar_meses(date(2026, 11, 30), 2) == date(2027, 1, 30)
