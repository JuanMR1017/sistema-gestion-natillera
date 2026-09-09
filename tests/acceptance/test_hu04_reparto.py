"""Aceptación HU-04: cierre y reparto anual proporcional (T049)."""

from datetime import date

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from tests.helpers import crear_usuario, login


@scenario("features/hu04_reparto.feature", "Reparto proporcional auditable")
def test_reparto_proporcional():
    pass


@scenario("features/hu04_reparto.feature", "Reparto ya ejecutado")
def test_reparto_duplicado():
    pass


@pytest.fixture()
def ctx():
    return {}


def _admin_y_datos(client, db):
    from app.models.ahorrador import Ahorrador
    from app.models.aporte import Aporte
    from app.models.cuota import Cuota
    from app.models.prestamo import Prestamo

    crear_usuario(db, "admin", rol="Administrador")
    login(client, "admin")
    client.post(
        "/admin/ahorradores",
        data={"nombre": "Ana", "documento": "123", "area": "Ventas",
              "fecha_ingreso": "2026-01-15"},
        follow_redirects=False,
    )
    a = db.query(Ahorrador).filter_by(documento="123").one()
    db.add_all([
        Aporte(ahorrador_id=a.id, fecha=date(2026, 1, 15), monto=125000,
               comprobante="T1", registrado_por="admin"),
        Aporte(ahorrador_id=a.id, fecha=date(2026, 2, 15), monto=125000,
               comprobante="T2", registrado_por="admin"),
    ])
    p = Prestamo(solicitante_id=a.id, monto=200000, plazo_meses=6, motivo="test",
                 tasa_mensual_aplicada=0.015, estado="Activo",
                 fecha_solicitud=date(2026, 2, 20), fecha_aprobacion=date(2026, 2, 21))
    db.add(p)
    db.flush()
    # Cuota con 10000 de interés totalmente cobrado (interés primero).
    db.add(Cuota(prestamo_id=p.id, numero=1, valor=100000, capital=90000,
                 interes=10000, fecha_vencimiento=date(2026, 3, 15),
                 abonado=100000, estado="Pagada"))
    db.commit()


@given("un ciclo con aportes de 250000 y una cuota con 10000 de interés cobrado")
def ciclo_con_datos(client, db):
    _admin_y_datos(client, db)


@when(parsers.parse('el administrador ejecuta el reparto del año {ano:d} con corte "{corte}"'))
def ejecuta_reparto(client, ctx, ano, corte):
    ctx["resp"] = client.post(
        "/admin/cierre",
        data={"ciclo_ano": str(ano), "fecha_corte": corte},
        follow_redirects=False,
    )


@then("cada integrante recibe su ahorro más la utilidad proporcional y el total cuadra con el fondo")
def reparto_cuadra(db, ctx):
    from app.models.reparto import Reparto

    assert ctx["resp"].status_code == 303
    r = db.query(Reparto).filter_by(ciclo_ano=2026).one()
    assert r.total_fondo == 260000  # 250000 aportes + 10000 intereses
    assert r.total_utilidades == 10000
    assert len(r.lineas) == 1
    linea = r.lineas[0]
    assert (linea.ahorro_aportado, linea.utilidad_proporcional, linea.total) == (
        250000, 10000, 260000)
    assert sum(li.total for li in r.lineas) == r.total_fondo


@given("un reparto ejecutado para el año 2026")
def reparto_previo(client, db, ctx):
    _admin_y_datos(client, db)
    r = client.post("/admin/cierre",
                    data={"ciclo_ano": "2026", "fecha_corte": "2026-12-31"},
                    follow_redirects=False)
    assert r.status_code == 303


@when("el administrador lo ejecuta de nuevo")
def ejecuta_duplicado(client, ctx):
    ctx["resp"] = client.post(
        "/admin/cierre",
        data={"ciclo_ano": "2026", "fecha_corte": "2026-12-31"},
    )


@then("es rechazado sin duplicar el reparto")
def rechazado(db, ctx):
    from app.models.reparto import Reparto

    assert ctx["resp"].status_code == 400
    assert db.query(Reparto).filter_by(ciclo_ano=2026).count() == 1
