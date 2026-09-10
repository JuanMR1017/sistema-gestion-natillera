"""Panel del ahorrador: dashboard, solicitudes y préstamos (FR-004, FR-005, HU-07, HU-02)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.deps import get_db, require_role
from app.models.ahorrador import Ahorrador
from app.models.notificacion import SOLICITUD_RECIBIDA
from app.models.parametro import TASA_MENSUAL, TOPE_PORCENTAJE_SALDO, vigente
from app.models.prestamo import PENDIENTE, Prestamo
from app.models.usuario import ROL_AHORRADOR
from app.services.finance import cuota_francesa
from app.services.mora import ahorrador_en_mora, evaluar_mora
from app.services.notificaciones import avisar_admins, texto_solicitud
from app.services.saldos import fondo_disponible, historial, saldo_acumulado

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PLAZO_MAXIMO_MESES = 60


def _ahorrador_de(db: Session, user) -> Ahorrador | None:
    return db.query(Ahorrador).filter_by(usuario_id=user.id).first()


def contexto_panel(db: Session, user) -> dict:
    """Contexto del dashboard (reusado por el despachador raíz)."""
    from app.models.parametro import MONTO_MINIMO_APORTE

    a = _ahorrador_de(db, user)
    saldo = saldo_acumulado(db, a.id) if a else 0
    movs = historial(db, a.id) if a else []
    tasa = float(vigente(db, TASA_MENSUAL))
    nombre = a.nombre if a else user.username
    iniciales = "".join(p[0] for p in nombre.split()[:2]).upper()
    try:
        minimo = int(float(vigente(db, MONTO_MINIMO_APORTE)))
    except ValueError:
        minimo = 0
    meta = minimo * 12  # meta anual derivada del mínimo periódico
    avance = round(min(saldo / meta * 100, 100)) if meta > 0 else None
    return {"saldo": saldo,
            "proyectado": int(saldo * tasa + 0.5),
            "tasa_pct": round(tasa * 100, 2),
            "aportes": movs,
            "nombre": nombre,
            "iniciales": iniciales,
            "naportes": len(movs),
            "meta": meta if meta > 0 else None,
            "avance": avance}


@router.get("/", response_class=HTMLResponse)
def panel(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_AHORRADOR)),
):
    return templates.TemplateResponse(
        request, "dashboard.html",
        {"request": request, **contexto_panel(db, user)})


@router.get("/prestamos", response_class=HTMLResponse)
def mis_prestamos(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_AHORRADOR)),
):
    a = _ahorrador_de(db, user)
    evaluar_mora(db)
    prestamos = (
        db.query(Prestamo).filter_by(solicitante_id=a.id)
        .order_by(Prestamo.fecha_solicitud.desc(), Prestamo.id.desc()).all()
        if a else []
    )
    return templates.TemplateResponse(
        request, "prestamos.html",
        {"request": request, "prestamos": prestamos},
    )


@router.get("/prestamos/nuevo", response_class=HTMLResponse)
def nuevo_prestamo(
    request: Request,
    monto: int | None = None,
    plazo_meses: int | None = None,
    motivo: str = "",
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_AHORRADOR)),
):
    tasa = float(vigente(db, TASA_MENSUAL))
    estimado = None
    if monto and plazo_meses and monto > 0 and 0 < plazo_meses <= PLAZO_MAXIMO_MESES:
        estimado = {"monto": monto, "plazo_meses": plazo_meses,
                    "cuota": cuota_francesa(monto, tasa, plazo_meses),
                    "tasa_pct": round(tasa * 100, 2)}
    return templates.TemplateResponse(
        request, "solicitud_prestamo.html",
        {"request": request, "estimado": estimado, "tasa_pct": round(tasa * 100, 2),
         "monto": monto or "", "plazo_meses": plazo_meses or "",
         "motivo": motivo,
         "plazo_maximo": PLAZO_MAXIMO_MESES},
    )


@router.post("/prestamos")
def crear_solicitud(
    request: Request,
    monto: int = Form(...),
    plazo_meses: int = Form(...),
    motivo: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_AHORRADOR)),
):
    def _error(msg):
        tasa = float(vigente(db, TASA_MENSUAL))
        return templates.TemplateResponse(
            request, "solicitud_prestamo.html",
            {"request": request, "error": msg, "estimado": None,
             "tasa_pct": round(tasa * 100, 2), "monto": monto,
             "plazo_meses": plazo_meses, "motivo": motivo,
             "plazo_maximo": PLAZO_MAXIMO_MESES},
            status_code=400,
        )

    a = _ahorrador_de(db, user)
    if a is None:
        return _error("Tu usuario aún no tiene perfil de ahorrador.")
    if not a.activo:
        return _error("Tu perfil de ahorrador está inactivo.")
    motivo = motivo.strip()
    if monto <= 0:
        return _error("El monto debe ser mayor que cero.")
    if not 1 <= plazo_meses <= PLAZO_MAXIMO_MESES:
        return _error(f"El plazo debe estar entre 1 y {PLAZO_MAXIMO_MESES} meses.")
    if not motivo:
        return _error("El motivo es obligatorio.")
    evaluar_mora(db)
    if ahorrador_en_mora(db, a.id):
        return _error("Tienes cuotas en mora. Ponte al día para solicitar un préstamo.")
    saldo = saldo_acumulado(db, a.id)
    tope_pct = float(vigente(db, TOPE_PORCENTAJE_SALDO))
    tope_saldo = int(saldo * tope_pct / 100)
    disponible = fondo_disponible(db)
    tope = min(tope_saldo, max(disponible, 0))
    if monto > tope:
        return _error(
            f"Tope aplicable: ${tope} (tope por saldo: ${tope_saldo}; "
            f"disponible del fondo: ${max(disponible, 0)})."
        )
    tasa = float(vigente(db, TASA_MENSUAL))
    hoy = datetime.now(UTC).date()
    p = Prestamo(solicitante_id=a.id, monto=monto, plazo_meses=plazo_meses,
                 motivo=motivo[:280], tasa_mensual_aplicada=tasa,
                 estado=PENDIENTE, fecha_solicitud=hoy)
    db.add(p)
    db.flush()
    avisar_admins(db, SOLICITUD_RECIBIDA,
                  texto_solicitud(p.id, a.nombre, monto, plazo_meses))
    db.commit()
    return RedirectResponse(url="/prestamos", status_code=303)
