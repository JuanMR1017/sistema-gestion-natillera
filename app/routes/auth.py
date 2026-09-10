"""Autenticación: login/logout por formulario con error genérico (FR-001, HU-05)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import deps
from app.deps import SESSION_COOKIE, SESSION_MAX_AGE, create_session, get_db, verify_password
from app.models.usuario import ROL_ADMINISTRADOR, Usuario

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PANEL_POR_ROL = {ROL_ADMINISTRADOR: "/admin"}
PANEL_DEFECTO = "/"

# Rate limit de login (T055): 20 fallos / 5 min por (IP, usuario) → 429.
VENTANA_RATE_SEG = 300
MAX_FALLOS_LOGIN = 20
_intentos: dict[tuple[str, str], list] = {}


def _llave(request: Request, username: str) -> tuple[str, str]:
    ip = request.client.host if request.client else "?"
    return (ip, username.strip())


def _poda(ahora: float, marcas: list) -> list:
    return [m for m in marcas if ahora - m < VENTANA_RATE_SEG]


def _bloqueado_por_rate(request: Request, username: str) -> bool:
    import time as _time

    marcas = _poda(_time.time(), _intentos.get(_llave(request, username), []))
    _intentos[_llave(request, username)] = marcas
    return len(marcas) >= MAX_FALLOS_LOGIN


def _registrar_fallo(request: Request, username: str) -> None:
    import time as _time

    llave = _llave(request, username)
    _intentos[llave] = _poda(_time.time(), _intentos.get(llave, [])) + [_time.time()]


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
    if _bloqueado_por_rate(request, username):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request,
             "error": "Demasiados intentos. Espera unos minutos."},
            status_code=429,
        )
    if user is None or not verify_password(password, user.password_hash):
        _registrar_fallo(request, username)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "error": "Credenciales inválidas."},
            status_code=401,
        )
    _intentos.pop(_llave(request, username), None)
    resp = RedirectResponse(url=panel_destino(user.rol), status_code=303)
    resp.set_cookie(SESSION_COOKIE, create_session(user.username), httponly=True,
                    max_age=SESSION_MAX_AGE)
    return resp


@router.post("/logout")
def hacer_logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp
