"""Aceptación HU-02/HU-03: solicitud, aprobación/rechazo, topes y mora (T026)."""

from datetime import UTC, datetime, timedelta

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from tests.helpers import crear_usuario, login


@scenario("features/hu0203_prestamos.feature", "Solicitar préstamo")
def test_solicitar():
    pass


@scenario("features/hu0203_prestamos.feature", "Aprobar préstamo genera tabla de cuotas")
def test_aprobar():
    pass


@scenario("features/hu0203_prestamos.feature", "Rechazar préstamo")
def test_rechazar():
    pass


@scenario("features/hu0203_prestamos.feature", "Cuota de referencia del prototipo")
def test_referencia():
    pass


@scenario("features/hu0203_prestamos.feature", "Tope de préstamo")
def test_tope():
    pass


@scenario("features/hu0203_prestamos.feature", "Mora bloquea solicitud")
def test_mora_bloquea():
    pass


@pytest.fixture()
def ctx():
    return {}


def _crear_ahorrador_con_credito(db, client, documento="777", username="sol", saldo=1000000):
    """Admin + ahorrador con usuario y aportes por `saldo`."""
    from app.models.ahorrador import Ahorrador

    crear_usuario(db, "admin", rol="Administrador")
    login(client, "admin")
    client.post(
        "/admin/ahorradores",
        data={"nombre": "Sol Pérez", "documento": documento, "area": "TI",
              "fecha_ingreso": "2026-01-10", "username": username,
              "password": "clave123"},
        follow_redirects=False,
    )
    a = db.query(Ahorrador).filter_by(documento=documento).one()
    client.post(
        "/admin/aportes",
        data={"ahorrador_id": str(a.id), "fecha": "2026-02-01",
              "monto": str(saldo), "comprobante": "TRX-S"},
        follow_redirects=False,
    )
    client.post("/logout")
    return a


def _login_ahorrador(client, username="sol"):
    r = client.post("/login", data={"username": username, "password": "clave123"},
                    follow_redirects=False)
    assert r.status_code == 303


def _solicitar(client, ctx, monto, plazo, motivo):
    ctx["resp"] = client.post(
        "/prestamos",
        data={"monto": str(monto), "plazo_meses": str(plazo), "motivo": motivo},
        follow_redirects=False,
    )


@given("un ahorrador con saldo disponible y sin mora")
def ahorrador_sin_mora(client, db, ctx):
    a = _crear_ahorrador_con_credito(db, client)
    ctx["ahorrador_id"] = a.id
    _login_ahorrador(client)


@when(parsers.parse('solicita un préstamo de {monto:d} a {plazo:d} meses por "{motivo}"'))
def solicita(client, ctx, monto, plazo, motivo):
    _solicitar(client, ctx, monto, plazo, motivo)


@then('la solicitud queda en "Pendiente" y se avisa al administrador')
def queda_pendiente(db, ctx):
    from app.models.notificacion import Notificacion
    from app.models.prestamo import Prestamo

    assert ctx["resp"].status_code == 303
    p = db.query(Prestamo).filter_by(solicitante_id=ctx["ahorrador_id"]).one()
    assert p.estado == "Pendiente"
    avisos = db.query(Notificacion).filter_by(tipo="solicitud_recibida").all()
    assert avisos, "el administrador debe recibir aviso de la solicitud"


@given('una solicitud "Pendiente" con liquidez suficiente')
def solicitud_pendiente(client, db, ctx):
    a = _crear_ahorrador_con_credito(db, client)
    ctx["ahorrador_id"] = a.id
    _login_ahorrador(client)
    _solicitar(client, ctx, 200000, 6, "Mejora de vivienda")
    assert ctx["resp"].status_code == 303
    client.post("/logout")
    login(client, "admin")


@when("el administrador la aprueba")
def aprueba(client, db, ctx):
    from app.models.prestamo import Prestamo

    p = db.query(Prestamo).filter_by(solicitante_id=ctx["ahorrador_id"]).one()
    ctx["prestamo_id"] = p.id
    ctx["resp"] = client.post(f"/admin/prestamos/{p.id}/aprobar",
                              follow_redirects=False)


@then("el préstamo genera su tabla de cuotas con intereses")
def tabla_generada(db, ctx):
    from app.models.prestamo import Prestamo

    assert ctx["resp"].status_code == 303
    p = db.get(Prestamo, ctx["prestamo_id"])
    assert p.estado in ("Aprobado", "Activo")
    assert len(p.cuotas) == 6
    assert sum(c.capital for c in p.cuotas) == p.monto
    assert all(c.valor == c.capital + c.interes for c in p.cuotas)
    assert all(c.estado == "Pendiente" for c in p.cuotas)


@given('una solicitud "Pendiente" de un ahorrador')
def solicitud_pendiente_rechazo(client, db, ctx):
    solicitud_pendiente(client, db, ctx)


@when(parsers.parse('el administrador la rechaza por "{motivo}"'))
def rechaza(client, db, ctx, motivo):
    from app.models.prestamo import Prestamo

    p = db.query(Prestamo).filter_by(solicitante_id=ctx["ahorrador_id"]).one()
    ctx["prestamo_id"] = p.id
    ctx["resp"] = client.post(f"/admin/prestamos/{p.id}/rechazar",
                              data={"motivo": motivo}, follow_redirects=False)


@then('la solicitud queda en "Rechazado" y se avisa al ahorrador')
def queda_rechazada(db, ctx):
    from app.models.notificacion import Notificacion
    from app.models.prestamo import Prestamo

    assert ctx["resp"].status_code == 303
    assert db.get(Prestamo, ctx["prestamo_id"]).estado == "Rechazado"
    assert db.query(Notificacion).filter_by(tipo="cambio_estado").count() >= 1


@given("la tasa mensual vigente es 1.8%")
def tasa_18(client, db):
    from datetime import date as _date

    from app.models.parametro import TASA_MENSUAL, Parametro, seed_defaults

    seed_defaults(db, _date(2026, 1, 1))
    row = db.query(Parametro).filter_by(clave=TASA_MENSUAL, vigente_hasta=None).one()
    row.vigente_hasta = _date(2026, 6, 30)
    db.add(Parametro(clave=TASA_MENSUAL, valor="0.018", vigente_desde=_date(2026, 7, 1),
                     vigente_hasta=None, modificado_por="test"))
    db.commit()
    _crear_ahorrador_con_credito(db, client, documento="REF", username="ref")
    _login_ahorrador(client, "ref")


@when(parsers.parse("se estima un préstamo de {monto:d} a {plazo:d} meses"))
def estima(client, ctx, monto, plazo):
    ctx["resp"] = client.get(f"/prestamos/nuevo?monto={monto}&plazo_meses={plazo}")


@then(parsers.parse("la cuota estimada es {cuota:d} con desglose de tasa visible"))
def cuota_referencia(ctx, cuota):
    assert ctx["resp"].status_code == 200
    cuerpo = ctx["resp"].text
    assert str(cuota) in cuerpo.replace(".", "").replace(",", "")
    assert "1.8" in cuerpo


@given(parsers.parse("un ahorrador con saldo {saldo:d}"))
def ahorrador_con_saldo(client, db, ctx, saldo):
    a = _crear_ahorrador_con_credito(db, client, saldo=saldo)
    ctx["ahorrador_id"] = a.id
    _login_ahorrador(client)


@then("la solicitud es bloqueada indicando el tope aplicable")
def bloqueada_tope(ctx):
    assert ctx["resp"].status_code == 400
    assert "tope" in ctx["resp"].text.lower()


@given("un ahorrador con una cuota en mora")
def ahorrador_en_mora(client, db, ctx):
    from app.models.cuota import Cuota
    from app.models.prestamo import Prestamo

    a = _crear_ahorrador_con_credito(db, client, saldo=500000)
    ctx["ahorrador_id"] = a.id
    hoy = datetime.now(UTC).date()
    p = Prestamo(solicitante_id=a.id, monto=100000, plazo_meses=6, motivo="Previo",
                 tasa_mensual_aplicada=0.015, estado="Activo",
                 fecha_solicitud=hoy - timedelta(days=40))
    db.add(p)
    db.flush()
    db.add(Cuota(prestamo_id=p.id, numero=1, valor=20000, capital=15000, interes=5000,
                 fecha_vencimiento=hoy - timedelta(days=10), abonado=0,
                 estado="Pendiente"))
    db.commit()
    _login_ahorrador(client)


@then("la solicitud es bloqueada hasta ponerse al día")
def bloqueada_mora(ctx):
    assert ctx["resp"].status_code == 400
    assert "mora" in ctx["resp"].text.lower()
