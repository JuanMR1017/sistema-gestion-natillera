"""Aceptación HU-09: reportes filtrables con exportación (T039)."""

from datetime import UTC, datetime, timedelta

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from tests.helpers import crear_usuario, login


@scenario("features/hu09_reportes.feature", "Reporte de aportes con descarga")
def test_reporte_aportes():
    pass


@scenario("features/hu09_reportes.feature", "Rango vacío sin error")
def test_rango_vacio():
    pass


@scenario("features/hu09_reportes.feature", "Reporte de mora con detalle")
def test_reporte_mora():
    pass


@pytest.fixture()
def ctx():
    return {}


def _fondo(client, db):
    from app.models.ahorrador import Ahorrador

    crear_usuario(db, "admin", rol="Administrador")
    login(client, "admin")
    for i, (nombre, doc) in enumerate([("Ana Ruiz", "R1"), ("Luis Paz", "R2")]):
        client.post(
            "/admin/ahorradores",
            data={"nombre": nombre, "documento": doc, "area": "TI",
                  "fecha_ingreso": "2026-01-10"},
            follow_redirects=False,
        )
        a = db.query(Ahorrador).filter_by(documento=doc).one()
        client.post(
            "/admin/aportes",
            data={"ahorrador_id": str(a.id), "fecha": f"2026-03-0{i + 1}",
                  "monto": "200000", "comprobante": f"TRX-{doc}"},
            follow_redirects=False,
        )


@given("movimientos registrados en el rango 2026-01-01 a 2026-12-31")
def movimientos(client, db):
    _fondo(client, db)


@when(parsers.parse("el administrador genera el reporte de aportes del rango"))
def genera_aportes(client, ctx):
    ctx["resp"] = client.get(
        "/admin/reportes?tipo=aportes&desde=2026-01-01&hasta=2026-12-31")


@then("ve los totales correctos y puede descargar Excel y PDF")
def totales_y_descargas(client, ctx):
    from io import BytesIO

    from openpyxl import load_workbook

    assert ctx["resp"].status_code == 200
    assert "400000" in ctx["resp"].text.replace(".", "").replace(",", "")
    for formato, ctype in (("xlsx", "spreadsheet"), ("pdf", "pdf")):
        r = client.get("/admin/reportes/descargar?tipo=aportes&desde=2026-01-01"
                       f"&hasta=2026-12-31&formato={formato}")
        assert r.status_code == 200, r.text[:200]
        assert ctype in r.headers["content-type"]
        assert "attachment" in r.headers["content-disposition"]
    r = client.get("/admin/reportes/descargar?tipo=aportes&desde=2026-01-01"
                   "&hasta=2026-12-31&formato=xlsx")
    wb = load_workbook(BytesIO(r.content))
    filas = list(wb.active.rows)
    assert len(filas) == 4  # encabezado + 2 aportes + total
    assert filas[-1][-1].value == 400000


@when(parsers.parse(
        "el administrador genera el reporte de aportes de {d1} a {d2}"))
def genera_vacio(client, ctx, d1, d2):
    ctx["resp"] = client.get(f"/admin/reportes?tipo=aportes&desde={d1}&hasta={d2}")


@then("ve la tabla vacía con totales en cero")
def tabla_ceros(client, ctx):
    assert ctx["resp"].status_code == 200
    assert "0" in ctx["resp"].text
    r = client.get("/admin/reportes/descargar?tipo=aportes&desde=2025-01-01"
                   "&hasta=2025-01-31&formato=xlsx")
    assert r.status_code == 200


@given("una cuota vencida impaga de un ahorrador")
def cuota_vencida(client, db, ctx):
    from app.models.ahorrador import Ahorrador
    from app.models.cuota import Cuota
    from app.models.prestamo import Prestamo

    _fondo(client, db)
    a = db.query(Ahorrador).filter_by(documento="R1").one()
    hoy = datetime.now(UTC).date()
    p = Prestamo(solicitante_id=a.id, monto=100000, plazo_meses=6, motivo="m",
                 tasa_mensual_aplicada=0.015, estado="Activo",
                 fecha_solicitud=hoy - timedelta(days=40))
    db.add(p)
    db.flush()
    db.add(Cuota(prestamo_id=p.id, numero=1, valor=20000, capital=15000,
                 interes=5000, fecha_vencimiento=hoy - timedelta(days=10),
                 abonado=0, estado="Pendiente"))
    db.commit()
    ctx["dias"] = 10


@when("el administrador genera el reporte de mora")
def genera_mora(client, ctx):
    ctx["resp"] = client.get("/admin/reportes?tipo=mora")


@then("cada cuota aparece con ahorrador, valor y días de mora")
def mora_detalle(ctx):
    cuerpo = ctx["resp"].text
    assert ctx["resp"].status_code == 200
    assert "R1" in cuerpo or "Ana Ruiz" in cuerpo
    assert "20000" in cuerpo.replace(".", "").replace(",", "")
    assert str(ctx["dias"]) in cuerpo
