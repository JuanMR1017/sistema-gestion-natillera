"""Aceptación HU-10: vencimiento, cambio de estado y recordatorio (T044)."""

from datetime import UTC, date, datetime, timedelta

import pytest
from pytest_bdd import given, scenario, then, when

from tests.helpers import crear_usuario, login


@scenario("features/hu10_notificaciones.feature", "Aviso por cambio de estado")
def test_cambio_estado():
    pass


@scenario("features/hu10_notificaciones.feature", "Alerta de vencimiento próximo")
def test_vencimiento():
    pass


@scenario("features/hu10_notificaciones.feature", "Recordatorio de aporte periódico")
def test_recordatorio():
    pass


@pytest.fixture()
def ctx():
    return {}


def _ahorrador(db, client, documento="AVI", username="avi", aporte_fecha="2026-02-01",
               aporte_monto=500000):
    from app.models.ahorrador import Ahorrador

    crear_usuario(db, "admin", rol="Administrador")
    login(client, "admin")
    client.post(
        "/admin/ahorradores",
        data={"nombre": "Avisado Gil", "documento": documento, "area": "TI",
              "fecha_ingreso": "2026-01-10", "username": username,
              "password": "clave123"},
        follow_redirects=False,
    )
    a = db.query(Ahorrador).filter_by(documento=documento).one()
    client.post(
        "/admin/aportes",
        data={"ahorrador_id": str(a.id), "fecha": aporte_fecha,
              "monto": str(aporte_monto), "comprobante": "TRX-A"},
        follow_redirects=False,
    )
    client.post("/logout")
    return a


@given("una solicitud de préstamo de un ahorrador")
def solicitud(client, db, ctx):
    from app.models.prestamo import Prestamo

    a = _ahorrador(db, client)
    ctx["ahorrador_id"] = a.id
    client.post("/login", data={"username": "avi", "password": "clave123"},
                follow_redirects=False)
    r = client.post("/prestamos", data={"monto": "100000", "plazo_meses": "6",
                                        "motivo": "aviso"},
                    follow_redirects=False)
    assert r.status_code == 303
    ctx["prestamo_id"] = db.query(Prestamo).filter_by(
        solicitante_id=a.id).one().id
    client.post("/logout")
    login(client, "admin")


@when("el administrador la aprueba")
def aprueba(client, ctx):
    ctx["resp"] = client.post(f"/admin/prestamos/{ctx['prestamo_id']}/aprobar",
                              follow_redirects=False)


@then("el ahorrador recibe el aviso con el nuevo estado")
def aviso_estado(client, ctx):
    assert ctx["resp"].status_code == 303
    client.post("/logout")
    client.post("/login", data={"username": "avi", "password": "clave123"},
                follow_redirects=False)
    r = client.get("/notificaciones")
    assert r.status_code == 200
    assert "aprobada" in r.text.lower()


@given("un préstamo con una cuota que vence en 2 días")
def cuota_por_vencer(client, db, ctx):
    from app.models.cuota import Cuota
    from app.models.prestamo import Prestamo

    a = _ahorrador(db, client, documento="VEN2", username="ven2")
    hoy = datetime.now(UTC).date()
    p = Prestamo(solicitante_id=a.id, monto=120000, plazo_meses=6, motivo="v",
                 tasa_mensual_aplicada=0.015, estado="Activo",
                 fecha_solicitud=hoy - timedelta(days=20))
    db.add(p)
    db.flush()
    c = Cuota(prestamo_id=p.id, numero=1, valor=25000, capital=20000, interes=5000,
              fecha_vencimiento=hoy + timedelta(days=2), abonado=0,
              estado="Pendiente")
    db.add(c)
    db.commit()
    ctx["valor"] = 25000
    ctx["vence"] = (hoy + timedelta(days=2)).isoformat()
    client.post("/login", data={"username": "ven2", "password": "clave123"},
                follow_redirects=False)


@when("el ahorrador abre sus avisos")
def abre_avisos(client, ctx):
    ctx["resp"] = client.get("/notificaciones")


@then("ve la alerta con cuota, valor y fecha límite")
def alerta_detalle(ctx):
    assert ctx["resp"].status_code == 200
    cuerpo = ctx["resp"].text
    assert "25000" in cuerpo.replace(".", "").replace(",", "")
    assert ctx["vence"] in cuerpo


@given("un ahorrador sin aportes en los últimos 40 días")
def sin_aportes(client, db, ctx):
    a = _ahorrador(db, client, documento="REC", username="rec",
                   aporte_fecha="2026-01-05", aporte_monto=100000)
    from app.models.aporte import Aporte

    db.query(Aporte).filter_by(ahorrador_id=a.id).update({"fecha":
        date.fromisoformat("2026-01-05")})
    # Simula antigüedad: el aporte queda fuera de la ventana de 30 días.
    assert (datetime.now(UTC).date() - date.fromisoformat("2026-01-05")).days > 30
    db.commit()
    ctx["ahorrador_id"] = a.id
    client.post("/login", data={"username": "rec", "password": "clave123"},
                follow_redirects=False)


@then("recibe el recordatorio con el monto mínimo vigente")
def recordatorio_detalle(client, db, ctx):
    from app.models.parametro import MONTO_MINIMO_APORTE, vigente

    assert ctx["resp"].status_code == 200
    minimo = vigente(db, MONTO_MINIMO_APORTE)
    assert "recordatorio" in ctx["resp"].text.lower()
    assert str(minimo) in ctx["resp"].text
