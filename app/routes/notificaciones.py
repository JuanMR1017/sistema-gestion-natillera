"""Avisos del usuario: alertas en plataforma (FR-010, HU-10)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models.notificacion import Notificacion
from app.services.notificaciones import generar_avisos_para_usuario

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/notificaciones", response_class=HTMLResponse)
def mis_avisos(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    generar_avisos_para_usuario(db, user)
    avisos = (
        db.query(Notificacion).filter_by(destinatario=user.username)
        .order_by(Notificacion.creada_en.desc(), Notificacion.id.desc())
        .limit(50).all()
    )
    return templates.TemplateResponse(
        request, "notificaciones.html",
        {"request": request, "avisos": avisos},
    )


@router.post("/notificaciones/{aviso_id}/leer")
def marcar_leida(
    aviso_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    n = db.get(Notificacion, aviso_id)
    if n is None or n.destinatario != user.username:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Aviso inexistente.")
    n.leida = True
    db.commit()
    return RedirectResponse(url="/notificaciones", status_code=303)
