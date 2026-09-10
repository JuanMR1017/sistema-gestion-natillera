"""Transversal: baja bloqueada, edición y parámetros versionados (T067, T068)."""

from datetime import date

from tests.helpers import crear_usuario, login


def _admin(client, db):
    crear_usuario(db, "admin", rol="Administrador")
    login(client, "admin")


def _crear(client, db, documento="B1", username="", password="clave123"):
    from app.models.ahorrador import Ahorrador

    datos = {"nombre": "Baja Test", "documento": documento, "area": "TI",
             "fecha_ingreso": "2026-01-10"}
    if username:
        datos.update({"username": username, "password": password})
    r = client.post("/admin/ahorradores", data=datos, follow_redirects=False)
    assert r.status_code == 303
    return db.query(Ahorrador).filter_by(documento=documento).one()


def test_baja_bloqueada_con_saldo(client, db):
    from app.models.aporte import Aporte

    _admin(client, db)
    a = _crear(client, db)
    db.add(Aporte(ahorrador_id=a.id, fecha=date(2026, 2, 1), monto=50000,
                  comprobante="T", registrado_por="admin"))
    db.commit()
    r = client.post(f"/admin/ahorradores/{a.id}/baja", follow_redirects=False)
    assert r.status_code == 400
    assert "sald" in r.text.lower()
    # Historial intacto.
    assert db.query(Aporte).filter_by(ahorrador_id=a.id).count() == 1


def test_baja_bloqueada_con_prestamo_vigente(client, db):
    from app.models.prestamo import Prestamo

    _admin(client, db)
    a = _crear(client, db, documento="B2")
    db.add(Prestamo(solicitante_id=a.id, monto=10000, plazo_meses=6, motivo="t",
                    tasa_mensual_aplicada=0.015, estado="Pendiente",
                    fecha_solicitud=date(2026, 3, 1)))
    db.commit()
    r = client.post(f"/admin/ahorradores/{a.id}/baja", follow_redirects=False)
    assert r.status_code == 400
    assert "préstamo" in r.text.lower()


def test_baja_ok_sin_saldo_ni_prestamos(client, db):

    _admin(client, db)
    a = _crear(client, db, documento="B3", username="baja3")
    r = client.post(f"/admin/ahorradores/{a.id}/baja", follow_redirects=False)
    assert r.status_code == 303
    db.refresh(a)
    assert a.activo is False
    # Inactivo no puede aportar ni solicitar.
    r = client.post("/admin/aportes",
                    data={"ahorrador_id": str(a.id), "fecha": "2026-04-01",
                          "monto": "1000", "comprobante": "X"},
                    follow_redirects=False)
    assert r.status_code == 400


def test_editar_ahorrador(client, db):
    _admin(client, db)
    a = _crear(client, db, documento="B4")
    r = client.post(f"/admin/ahorradores/{a.id}/editar",
                    data={"nombre": "Nuevo Nombre", "area": "Ventas",
                          "fecha_ingreso": "2026-01-20"},
                    follow_redirects=False)
    assert r.status_code == 303
    db.refresh(a)
    assert (a.nombre, a.area) == ("Nuevo Nombre", "Ventas")
    assert a.documento == "B4"  # documento inmutable: preserva historial


def test_parametros_versionados_via_http(client, db):
    from datetime import date as _date

    from app.models.parametro import TASA_MENSUAL, Parametro, seed_defaults, vigente

    _admin(client, db)
    seed_defaults(db, _date(2026, 1, 1))
    r = client.get("/admin/parametros")
    assert r.status_code == 200
    r = client.post("/admin/parametros",
                    data={"clave": TASA_MENSUAL, "valor": "0.02",
                          "vigente_desde": "2026-07-01"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert vigente(db, TASA_MENSUAL) == "0.02"
    cerradas = db.query(Parametro).filter_by(clave=TASA_MENSUAL).all()
    assert sum(1 for p in cerradas if p.vigente_hasta is None) == 1
    assert sum(1 for p in cerradas if p.modificado_por == "admin") >= 1
    # Valor inválido se rechaza sin romper vigencia.
    r = client.post("/admin/parametros",
                    data={"clave": TASA_MENSUAL, "valor": "99",
                          "vigente_desde": "2026-08-01"})
    assert r.status_code == 400
    assert vigente(db, TASA_MENSUAL) == "0.02"
