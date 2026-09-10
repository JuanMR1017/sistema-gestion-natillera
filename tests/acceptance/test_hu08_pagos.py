"""Aceptación HU-08: abonos total/parcial, recálculo y mora (T034)."""

from datetime import UTC, datetime, timedelta

import pytest
from pytest_bdd import given, scenario, then, when

from tests.helpers import crear_usuario, login


@scenario("features/hu08_pagos.feature", "Abono total de cuota")
def test_abono_total():
    pass


@scenario("features/hu08_pagos.feature", "Abono parcial de cuota")
def test_abono_parcial():
    pass


@scenario("features/hu08_pagos.feature", "Pago pone al día y desbloquea")
def test_desbloqueo():
    pass


@scenario("features/hu08_pagos.feature", "Mora automática por días de gracia")
def test_mora_auto():
    pass


@pytest.fixture()
def ctx():
    return {}


def _fondo_con_prestamo(client, db, documento="PAG", username="pag",
                        aporte=1000000, monto=600000, plazo=6):
    """Admin + ahorrador con aporte, solicitud aprobada vía HTTP."""
    from app.models.ahorrador import Ahorrador
    from app.models.prestamo import Prestamo

    crear_usuario(db, "admin", rol="Administrador")
    login(client, "admin")
    client.post(
        "/admin/ahorradores",
        data={"nombre": "Paga Todo", "documento": documento, "area": "TI",
              "fecha_ingreso": "2026-01-10", "username": username,
              "password": "clave123"},
        follow_redirects=False,
    )
    a = db.query(Ahorrador).filter_by(documento=documento).one()
    client.post(
        "/admin/aportes",
        data={"ahorrador_id": str(a.id), "fecha": "2026-02-01",
              "monto": str(aporte), "comprobante": "TRX-P"},
        follow_redirects=False,
    )
    client.post("/logout")
    client.post("/login", data={"username": username, "password": "clave123"},
                follow_redirects=False)
    r = client.post(
        "/prestamos",
        data={"monto": str(monto), "plazo_meses": str(plazo), "motivo": "Prueba"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    client.post("/logout")
    login(client, "admin")
    p = db.query(Prestamo).filter_by(solicitante_id=a.id).one()
    r = client.post(f"/admin/prestamos/{p.id}/aprobar", follow_redirects=False)
    assert r.status_code == 303
    db.refresh(p)
    return a, p


def _pagar(client, ctx, cuota_id, valor, fecha="2026-05-01"):
    ctx["resp"] = client.post(
        "/admin/pagos",
        data={"cuota_id": str(cuota_id), "valor": str(valor), "fecha": fecha},
        follow_redirects=False,
    )


@given("un préstamo activo con cuotas pendientes")
def prestamo_activo(client, db, ctx):
    a, p = _fondo_con_prestamo(client, db)
    ctx["ahorrador_id"] = a.id
    ctx["prestamo_id"] = p.id
    ctx["cuota_id"] = p.cuotas[0].id
    ctx["cuota_valor"] = p.cuotas[0].valor


@when("el administrador registra el abono total de la primera cuota")
def abono_total(client, ctx):
    _pagar(client, ctx, ctx["cuota_id"], ctx["cuota_valor"])


@then('la cuota queda "Pagada" y el saldo pendiente se recalcula')
def cuota_pagada(db, ctx):
    from app.models.cuota import Cuota
    from app.models.prestamo import Prestamo
    from app.services.mora import saldo_pendiente

    assert ctx["resp"].status_code == 303
    c = db.get(Cuota, ctx["cuota_id"])
    assert c.estado == "Pagada"
    assert c.abonado == c.valor
    p = db.get(Prestamo, ctx["prestamo_id"])
    assert saldo_pendiente(p) == sum(c2.valor - c2.abonado for c2 in p.cuotas)
    assert saldo_pendiente(p) == sum(c2.valor for c2 in p.cuotas[1:])


@when("el administrador registra un abono parcial de la primera cuota")
def abono_parcial(client, ctx):
    _pagar(client, ctx, ctx["cuota_id"], ctx["cuota_valor"] // 2)


@then('la cuota queda "Parcial" con el remanente visible')
def cuota_parcial(client, db, ctx):
    from app.models.cuota import Cuota

    assert ctx["resp"].status_code == 303
    c = db.get(Cuota, ctx["cuota_id"])
    assert c.estado == "Parcial"
    r = client.get("/admin/cartera")
    assert r.status_code == 200
    assert str(c.valor - c.abonado) in r.text


@given("un ahorrador en mora por una cuota vencida")
def en_mora(client, db, ctx):

    a, p = _fondo_con_prestamo(client, db, documento="MOR", username="mor")
    ctx["ahorrador_id"] = a.id
    ctx["prestamo_id"] = p.id
    c = p.cuotas[0]
    c.fecha_vencimiento = datetime.now(UTC).date() - timedelta(days=10)
    db.commit()
    ctx["cuota_id"] = c.id
    ctx["cuota_valor"] = c.valor - c.abonado
    # Verificar bloqueo vigente.
    client.post("/logout")
    client.post("/login", data={"username": "mor", "password": "clave123"},
                follow_redirects=False)
    r = client.post("/prestamos", data={"monto": "50000", "plazo_meses": "6",
                                        "motivo": "x"}, follow_redirects=False)
    assert r.status_code == 400 and "mora" in r.text.lower()
    client.post("/logout")
    login(client, "admin")


@when("registra el pago que lo pone al día")
def paga_al_dia(client, ctx):
    _pagar(client, ctx, ctx["cuota_id"], ctx["cuota_valor"],
           fecha=datetime.now(UTC).date().isoformat())


@then("puede solicitar un préstamo nuevo")
def desbloqueado(client, ctx):
    client.post("/logout")
    r = client.post("/login", data={"username": "mor", "password": "clave123"},
                    follow_redirects=False)
    assert r.status_code == 303
    r = client.post("/prestamos", data={"monto": "50000", "plazo_meses": "6",
                                        "motivo": "nuevo"}, follow_redirects=False)
    assert r.status_code == 303


@given("un préstamo con una cuota vencida hace 10 días sin pago")
def cuota_vencida(client, db, ctx):

    a, p = _fondo_con_prestamo(client, db, documento="VEN", username="ven")
    ctx["ahorrador_id"] = a.id
    c = p.cuotas[0]
    c.fecha_vencimiento = datetime.now(UTC).date() - timedelta(days=10)
    db.commit()
    ctx["cuota_id"] = c.id


@when("se evalúa la cartera")
def evalua_cartera(client, ctx):
    ctx["resp"] = client.get("/admin/cartera")


@then("la cuota y el ahorrador quedan en mora y visibles en cartera")
def mora_visible(db, ctx):
    from app.models.ahorrador import Ahorrador
    from app.models.cuota import Cuota

    assert ctx["resp"].status_code == 200
    c = db.get(Cuota, ctx["cuota_id"])
    assert c.estado == "En mora"
    a = db.get(Ahorrador, ctx["ahorrador_id"])
    cuerpo = ctx["resp"].text.lower()
    assert "mora" in cuerpo
    assert a.documento.lower() in cuerpo or a.nombre.lower() in cuerpo
