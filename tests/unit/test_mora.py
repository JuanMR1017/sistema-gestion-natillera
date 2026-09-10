"""Unitarias de mora automática: gracia 5 parametrizable y bloqueo RN-04 (T035)."""

from datetime import UTC, date, datetime, timedelta

from app.models.parametro import DIAS_GRACIA_MORA, Parametro, seed_defaults
from app.services.mora import (
    ahorrador_en_mora,
    cuota_en_mora,
    dias_gracia,
    evaluar_mora,
)


class _Cuota:
    def __init__(self, estado, vencimiento):
        self.estado = estado
        self.fecha_vencimiento = vencimiento


def test_gracia_por_defecto_cinco_y_parametrizable(db):
    seed_defaults(db, date(2026, 1, 1))
    assert dias_gracia(db) == 5
    row = db.query(Parametro).filter_by(clave=DIAS_GRACIA_MORA,
                                        vigente_hasta=None).one()
    row.vigente_hasta = date(2026, 6, 30)
    db.add(Parametro(clave=DIAS_GRACIA_MORA, valor="10",
                     vigente_desde=date(2026, 7, 1), vigente_hasta=None,
                     modificado_por="test"))
    db.commit()
    assert dias_gracia(db) == 10


def test_borde_gracia_no_es_mora_pero_un_dia_mas_si():
    hoy = date(2026, 3, 10)
    assert not cuota_en_mora(_Cuota("Pendiente", hoy - timedelta(days=5)), hoy, 5)
    assert cuota_en_mora(_Cuota("Pendiente", hoy - timedelta(days=6)), hoy, 5)
    assert not cuota_en_mora(_Cuota("Pagada", hoy - timedelta(days=60)), hoy, 5)


def test_bloqueo_rn04_se_levanta_al_ponerse_al_dia(db):
    """Mora marca En mora y bloquea; al saldar la cuota, se levanta."""
    from app import deps as _deps
    from app.models.ahorrador import Ahorrador
    from app.models.cuota import Cuota
    from app.models.prestamo import Prestamo
    from app.models.usuario import Usuario

    seed_defaults(db, date(2026, 1, 1))
    u = Usuario(username="m", password_hash=_deps.hash_password("x"), rol="Ahorrador")
    db.add(u)
    db.flush()
    a = Ahorrador(nombre="M", documento="M1", area="TI",
                  fecha_ingreso=date(2026, 1, 1), usuario_id=u.id)
    db.add(a)
    db.flush()
    hoy = datetime.now(UTC).date()
    p = Prestamo(solicitante_id=a.id, monto=100000, plazo_meses=6, motivo="t",
                 tasa_mensual_aplicada=0.015, estado="Aprobado",
                 fecha_solicitud=hoy - timedelta(days=40))
    db.add(p)
    db.flush()
    c = Cuota(prestamo_id=p.id, numero=1, valor=20000, capital=15000, interes=5000,
              fecha_vencimiento=hoy - timedelta(days=10), abonado=0,
              estado="Pendiente")
    db.add(c)
    db.commit()

    assert ahorrador_en_mora(db, a.id, hoy) is True
    db.refresh(c)
    assert c.estado == "En mora"

    # Pago total que pone al día (vía motor, como haría la ruta).
    from app.services.finance import imputar_pago

    _, _, nuevo, estado = imputar_pago(c.valor, c.capital, c.interes, c.abonado,
                                       c.valor - c.abonado)
    c.abonado, c.estado = nuevo, estado
    db.commit()
    evaluar_mora(db, hoy)
    assert ahorrador_en_mora(db, a.id, hoy) is False
