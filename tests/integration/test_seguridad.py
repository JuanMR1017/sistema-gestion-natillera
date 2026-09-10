"""Seguridad: rate limit de login y expiración de sesión (T055)."""

from tests.helpers import crear_usuario


def test_rate_limit_bloquea_tras_20_fallos(client, db):
    crear_usuario(db, "victima", password="secreta", rol="Ahorrador")
    for _ in range(20):
        r = client.post("/login", data={"username": "victima",
                                        "password": "mala"},
                        follow_redirects=False)
        assert r.status_code == 401
    r = client.post("/login", data={"username": "victima", "password": "mala"},
                    follow_redirects=False)
    assert r.status_code == 429
    # Otro usuario no afectado por el bloqueo.
    crear_usuario(db, "otro", password="clave123", rol="Ahorrador")
    r = client.post("/login", data={"username": "otro", "password": "clave123"},
                    follow_redirects=False)
    assert r.status_code == 303


def test_sesion_expira():
    from app import deps

    token = deps.create_session("alguien")
    assert deps.read_session(token) == "alguien"
    assert deps.read_session(token, max_age=-1) is None
    assert deps.read_session("manipulado") is None


def test_acceso_cruzado_403(client, db):
    from tests.helpers import login

    crear_usuario(db, "ah", rol="Ahorrador")
    login(client, "ah")
    assert client.get("/admin").status_code == 403
    assert client.get("/admin/cartera").status_code == 403
