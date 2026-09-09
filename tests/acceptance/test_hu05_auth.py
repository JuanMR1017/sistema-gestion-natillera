"""Aceptación HU-05: autenticación por roles y error genérico (T013)."""

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from tests.helpers import crear_usuario


@scenario("features/hu05_auth.feature", "Ahorrador inicia sesión")
def test_ahorrador_login():
    pass


@scenario("features/hu05_auth.feature", "Administrador inicia sesión")
def test_admin_login():
    pass


@scenario("features/hu05_auth.feature", "Credenciales inválidas")
def test_credenciales_invalidas():
    pass


@pytest.fixture()
def ctx():
    return {}


@given(parsers.parse('un usuario "{username}" con rol "{rol}" y contraseña "{password}"'))
def usuario_registrado(db, ctx, username, rol, password):
    ctx["username"] = username
    ctx["password"] = password
    ctx["rol"] = rol
    crear_usuario(db, username, password, rol)


@when("ingresa sus credenciales correctas")
def ingresa_correctas(client, ctx):
    ctx["resp"] = client.post(
        "/login",
        data={"username": ctx["username"], "password": ctx["password"]},
        follow_redirects=False,
    )


@when("ingresa una contraseña incorrecta")
def ingresa_mala(client, ctx):
    ctx["resp"] = client.post(
        "/login",
        data={"username": ctx["username"], "password": "otra-clave"},
        follow_redirects=False,
    )


@then("es redirigido a su panel de ahorrador con sesión activa")
def panel_ahorrador(client, ctx):
    assert ctx["resp"].status_code == 303
    assert ctx["resp"].headers["location"] == "/"
    assert "natillera_session" in (ctx["resp"].headers.get("set-cookie") or "")


@then("es redirigido al panel de administración con sesión activa")
def panel_admin(client, ctx):
    assert ctx["resp"].status_code == 303
    assert ctx["resp"].headers["location"] == "/admin"
    assert "natillera_session" in (ctx["resp"].headers.get("set-cookie") or "")


@then("ve un error genérico sin revelar el dato fallido")
def error_generico(ctx):
    assert ctx["resp"].status_code == 401
    cuerpo = ctx["resp"].text.lower()
    assert "credenciales" in cuerpo and "inválidas" in cuerpo
    # No debe indicar cuál de los dos datos falló:
    assert "no existe" not in cuerpo
    assert "incorrecta" not in cuerpo
    assert "inexistente" not in cuerpo
