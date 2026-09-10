"""App FastAPI: logging estructurado, estáticos, plantillas y montaje de rutas."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("natillera")

app = FastAPI(title="Sistema de Gestión de Natillera")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Routers por historia (se registran tras el despachador raíz para que
# GET / despache por rol antes que el panel del ahorrador):
from app import deps as _deps
from app.models.usuario import Usuario as _Usuario
from app.routes import admin, ahorrador, auth, notificaciones
from app.routes.ahorrador import contexto_panel as _contexto_panel
from app.routes.auth import panel_destino as _panel_destino


@app.get("/", include_in_schema=False)
def raiz(request: Request, db: Session = Depends(_deps.get_db)):
    username = _deps.read_session(request.cookies.get(_deps.SESSION_COOKIE))
    user = (db.query(_Usuario).filter_by(username=username, activo=True).first()
            if username else None)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    destino = _panel_destino(user.rol)
    if destino != "/":
        return RedirectResponse(url=destino, status_code=303)
    return ahorrador.templates.TemplateResponse(
        request, "dashboard.html",
        {"request": request, **_contexto_panel(db, user)})


app.include_router(auth.router)
app.include_router(ahorrador.router)
app.include_router(admin.router)
app.include_router(notificaciones.router)


@app.get("/salud", include_in_schema=False)
def salud():
    return {"estado": "ok"}
