"""Integración de roles: denegación cruzada y 401 sin sesión (T014)."""

from tests.helpers import crear_usuario, login


def test_ahorrador_en_ruta_admin_recibe_403(client, db):
    crear_usuario(db, "juan", rol="Ahorrador")
    login(client, "juan")
    r = client.get("/admin")
    assert r.status_code == 403


def test_sin_sesion_en_ruta_admin_recibe_401(client):
    r = client.get("/admin")
    assert r.status_code == 401


def test_admin_en_su_panel_recibe_200(client, db):
    crear_usuario(db, "admin", rol="Administrador")
    login(client, "admin")
    r = client.get("/admin")
    assert r.status_code == 200
