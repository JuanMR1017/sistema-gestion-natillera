"""Autenticación: login/logout por formulario con error genérico (FR-001, HU-05)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import deps
from app.deps import SESSION_COOKIE, create_session, get_db, verify_password
from app.models.usuario import ROL_ADMINISTRADOR, Usuario

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PANEL_POR_ROL = {ROL_ADMINISTRADOR: "/admin"}
PANEL_DEFECTO = "/"


def panel_destino(rol: str) -> str:
    return PANEL_POR_ROL.get(rol, PANEL_DEFECTO)


@router.get("/login", response_class=HTMLResponse)
def ver_login(request: Request, db: Session = Depends(get_db)):
    username = deps.read_session(request.cookies.get(SESSION_COOKIE))
    if username and db.query(Usuario).filter_by(username=username, activo=True).first():
        user = db.query(Usuario).filter_by(username=username).first()
        return RedirectResponse(url=panel_destino(user.rol), status_code=303)
    return templates.TemplateResponse(request, "login.html", {"request": request})


@router.post("/login")
def hacer_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(Usuario).filter_by(username=username.strip(), activo=True).first()
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "error": "Credenciales inválidas."},
            status_code=401,
        )
    resp = RedirectResponse(url=panel_destino(user.rol), status_code=303)
    resp.set_cookie(SESSION_COOKIE, create_session(user.username), httponly=True)
    return resp


@router.post("/logout")
def hacer_logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp
