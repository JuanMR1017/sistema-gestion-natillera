"""Aceptación HU-06/HU-01/HU-07: ahorradores, aportes y saldo (T018)."""

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from tests.helpers import crear_usuario, login


@scenario("features/hu060107_aportes.feature", "Registrar ahorrador")
def test_registrar_ahorrador():
    pass


@scenario("features/hu060107_aportes.feature", "Registrar aporte")
def test_registrar_aporte():
    pass


@scenario("features/hu060107_aportes.feature", "Consultar saldo")
def test_consultar_saldo():
    pass


@scenario("features/hu060107_aportes.feature", "Documento duplicado")
def test_documento_duplicado():
    pass


@pytest.fixture()
def ctx():
    return {}


def _login_admin(client, db):
    crear_usuario(db, "admin", rol="Administrador")
    login(client, "admin")


@given("un administrador autenticado en el módulo de ahorradores")
def admin_en_modulo(client, db, ctx):
    _login_admin(client, db)
    r = client.get("/admin/ahorradores")
    assert r.status_code == 200


@when(
    parsers.parse(
        'registra nombre "{nombre}", documento "{documento}", área "{area}"'
        ' y fecha de ingreso "{ingreso}"'
    )
)
def registra_ahorrador(client, ctx, nombre, documento, area, ingreso):
    ctx["resp"] = client.post(
        "/admin/ahorradores",
        data={"nombre": nombre, "documento": documento, "area": area,
              "fecha_ingreso": ingreso},
        follow_redirects=False,
    )


@then("el ahorrador queda creado con saldo inicial en cero y disponible para aportes")
def ahorrador_creado(db, ctx):
    from app.models.ahorrador import Ahorrador

    assert ctx["resp"].status_code == 303
    a = db.query(Ahorrador).filter_by(documento="123").one()
    assert a.nombre == "Ana Ruiz"
    assert a.saldo() == 0


@given(parsers.parse('un ahorrador activo con documento "{documento}"'))
def ahorrador_activo(client, db, ctx, documento):
    _login_admin(client, db)
    r = client.post(
        "/admin/ahorradores",
        data={"nombre": "Ana Ruiz", "documento": documento, "area": "Ventas",
              "fecha_ingreso": "2026-01-15"},
        follow_redirects=False,
    )
    assert r.status_code == 303


@when(parsers.parse("el administrador registra un aporte de {monto:d} con fecha {fecha}"))
def registra_aporte(client, db, ctx, monto, fecha):
    from app.models.ahorrador import Ahorrador

    a = db.query(Ahorrador).filter_by(documento="123").one()
    ctx["ahorrador_id"] = a.id
    ctx["resp"] = client.post(
        "/admin/aportes",
        data={"ahorrador_id": str(a.id), "fecha": fecha.strip('"'),
              "monto": str(monto), "comprobante": "TRX-1"},
        follow_redirects=False,
    )


@then(parsers.parse("el saldo del ahorrador aumenta en {monto:d} y el fondo total se actualiza"))
def saldo_aumenta(db, ctx, monto):
    from app.models.ahorrador import Ahorrador
    from app.services.saldos import fondo_total, saldo_acumulado

    assert ctx["resp"].status_code == 303
    a = db.query(Ahorrador).get(ctx["ahorrador_id"])
    assert saldo_acumulado(db, a.id) == monto
    assert fondo_total(db) == monto


@given("un ahorrador autenticado con 2 aportes de 125000")
def ahorrador_con_aportes(client, db, ctx):
    from app.models.ahorrador import Ahorrador

    _login_admin(client, db)
    client.post(
        "/admin/ahorradores",
        data={"nombre": "Juan", "documento": "456", "area": "TI",
              "fecha_ingreso": "2026-01-10", "username": "juan", "password": "clave123"},
        follow_redirects=False,
    )
    a = db.query(Ahorrador).filter_by(documento="456").one()
    for fecha in ("2026-01-15", "2026-02-15"):
        r = client.post(
            "/admin/aportes",
            data={"ahorrador_id": str(a.id), "fecha": fecha, "monto": "125000",
                  "comprobante": f"TRX-{fecha}"},
            follow_redirects=False,
        )
        assert r.status_code == 303
    client.post("/logout")
    r = client.post("/login", data={"username": "juan", "password": "clave123"},
                    follow_redirects=False)
    assert r.status_code == 303


@when('abre "Mi saldo"')
def abre_saldo(client, ctx):
    ctx["resp"] = client.get("/")


@then(
    parsers.parse(
        "ve saldo acumulado {saldo:d}, rendimiento proyectado y el historial ordenado por fecha"
    )
)
def ve_saldo(ctx, saldo):
    cuerpo = ctx["resp"].text
    assert ctx["resp"].status_code == 200
    assert str(saldo) in cuerpo.replace(".", "").replace(",", "") or str(saldo) in cuerpo
    assert "2026-01-15" in cuerpo and "2026-02-15" in cuerpo
    assert cuerpo.index("2026-01-15") < cuerpo.index("2026-02-15")
    assert "proyectado" in cuerpo.lower()


@given(parsers.parse('un ahorrador con documento "{documento}"'))
def ya_existe(client, db, documento):
    _login_admin(client, db)
    client.post(
        "/admin/ahorradores",
        data={"nombre": "Ana", "documento": documento, "area": "Ventas",
              "fecha_ingreso": "2026-01-15"},
        follow_redirects=False,
    )


@when(parsers.parse('el administrador registra otro ahorrador con documento "{documento}"'))
def registra_duplicado(client, ctx, documento):
    ctx["resp"] = client.post(
        "/admin/ahorradores",
        data={"nombre": "Otra", "documento": documento, "area": "TI",
              "fecha_ingreso": "2026-02-01"},
    )


@then("el registro es rechazado sin crear duplicados")
def rechazado(db, ctx):
    from app.models.ahorrador import Ahorrador

    assert ctx["resp"].status_code == 400
    assert db.query(Ahorrador).filter_by(documento="123").count() == 1
