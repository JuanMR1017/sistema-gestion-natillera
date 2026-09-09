"""Unitarias de saldos derivados: nunca editados a mano (T019)."""

from datetime import date

from app.models.ahorrador import Ahorrador
from app.models.aporte import Aporte
from app.services.saldos import fondo_total, saldo_acumulado


def _ahorrador(db, documento="123"):
    a = Ahorrador(nombre="Ana", documento=documento, area="Ventas",
                  fecha_ingreso=date(2026, 1, 15))
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def test_saldo_es_cero_sin_aportes(db):
    a = _ahorrador(db)
    assert saldo_acumulado(db, a.id) == 0
    assert a.saldo() == 0


def test_saldo_suma_aportes_exactamente_una_vez(db):
    a = _ahorrador(db)
    db.add_all([
        Aporte(ahorrador_id=a.id, fecha=date(2026, 1, 15), monto=125000,
               comprobante="T1", registrado_por="admin"),
        Aporte(ahorrador_id=a.id, fecha=date(2026, 2, 15), monto=125000,
               comprobante="T2", registrado_por="admin"),
    ])
    db.commit()
    assert saldo_acumulado(db, a.id) == 250000
    assert fondo_total(db) == 250000


def test_saldo_es_derivado_no_columna(db):
    assert "saldo" not in Ahorrador.__table__.columns
