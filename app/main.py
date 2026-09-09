"""App FastAPI: logging estructurado, estáticos, plantillas y montaje de rutas."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("natillera")

app = FastAPI(title="Sistema de Gestión de Natillera")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Routers por historia (se registran al implementar cada línea):
from app.routes import admin, ahorrador, auth

app.include_router(auth.router)
app.include_router(ahorrador.router)
app.include_router(admin.router)


@app.get("/", include_in_schema=False)
def raiz(request: Request):
    from app import deps
    from app.models.usuario import Usuario
    from app.routes.auth import panel_destino

    username = deps.read_session(request.cookies.get(deps.SESSION_COOKIE))
    if username:
        db = next(deps.get_db())
        try:
            user = db.query(Usuario).filter_by(username=username, activo=True).first()
        finally:
            db.close()
        if user is not None:
            return RedirectResponse(url=panel_destino(user.rol), status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/salud", include_in_schema=False)
def salud():
    return {"estado": "ok"}
