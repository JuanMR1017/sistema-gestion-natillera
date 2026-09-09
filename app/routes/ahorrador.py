"""Panel del ahorrador: dashboard con saldo, proyectado e historial (FR-004, HU-07)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.deps import get_db, require_role
from app.models.ahorrador import Ahorrador
from app.models.parametro import TASA_MENSUAL, vigente
from app.models.usuario import ROL_AHORRADOR
from app.services.saldos import historial, saldo_acumulado

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def panel(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_AHORRADOR)),
):
    a = db.query(Ahorrador).filter_by(usuario_id=user.id).first()
    saldo = saldo_acumulado(db, a.id) if a else 0
    movs = historial(db, a.id) if a else []
    tasa = float(vigente(db, TASA_MENSUAL))
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"request": request, "saldo": saldo,
         "proyectado": int(saldo * tasa + 0.5),
         "tasa_pct": round(tasa * 100, 2), "aportes": movs},
    )
