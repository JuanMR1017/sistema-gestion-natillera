"""Validación quickstart QS-1–QS-8: ninguna ruta contratada devuelve 404 (T056)."""

import pytest

from tests.helpers import crear_usuario, login


@pytest.fixture()
def poblado(client, db):
    from app.models.ahorrador import Ahorrador

    crear_usuario(db, "admin", rol="Administrador")
    login(client, "admin")
    client.post(
        "/admin/ahorradores",
        data={"nombre": "QS Uno", "documento": "QS1", "area": "TI",
              "fecha_ingreso": "2026-01-10", "username": "qs1",
              "password": "clave123"},
        follow_redirects=False,
    )
    a = db.query(Ahorrador).filter_by(documento="QS1").one()
    client.post(
        "/admin/aportes",
        data={"ahorrador_id": str(a.id), "fecha": "2026-02-01",
              "monto": "300000", "comprobante": "QS-T"},
        follow_redirects=False,
    )
    return a


RUTAS_ADMIN_OK = [
    "/admin", "/admin/ahorradores", "/admin/aportes", "/admin/prestamos",
    "/admin/cartera", "/admin/reportes", "/admin/parametros", "/admin/cierre",
    "/admin/reportes?tipo=fondos", "/admin/reportes/descargar?tipo=fondos&formato=xlsx",
    "/admin/reportes/descargar?tipo=fondos&formato=pdf",
]

RUTAS_AHORRADOR_OK = ["/", "/prestamos", "/prestamos/nuevo", "/notificaciones"]


def test_rutas_admin_sin_404(client, db, poblado):
    for ruta in RUTAS_ADMIN_OK:
        r = client.get(ruta)
        assert r.status_code in (200, 303), f"{ruta} → {r.status_code}"


def test_rutas_ahorrador_sin_404(client, db, poblado):
    client.post("/logout")
    login(client, "qs1")
    for ruta in RUTAS_AHORRADOR_OK:
        r = client.get(ruta)
        assert r.status_code in (200, 303), f"{ruta} → {r.status_code}"


def test_raiz_redirige_segun_rol(client, db, poblado):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/admin"
    client.post("/logout")
    assert client.get("/", follow_redirects=False).headers["location"] == "/login"
    assert client.get("/login").status_code == 200
