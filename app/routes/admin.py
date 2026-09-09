"""Panel de administración: índice, ahorradores, aportes y cierre (FR-002, FR-003, FR-011)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import deps
from app.deps import get_db, require_role
from app.models.ahorrador import Ahorrador
from app.models.aporte import Aporte
from app.models.reparto import Reparto
from app.models.usuario import ROL_ADMINISTRADOR, ROL_AHORRADOR, Usuario
from app.services.reparto import ejecutar_reparto

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/admin", response_class=HTMLResponse)
def panel(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    return templates.TemplateResponse(
        request,
        "admin.html",
        {"request": request, "total_usuarios": db.query(Usuario).count()},
    )


def _hoy():
    return datetime.now(UTC).date()


@router.get("/admin/ahorradores", response_class=HTMLResponse)
def ver_ahorradores(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    return templates.TemplateResponse(
        request,
        "admin_ahorradores.html",
        {"request": request, "ahorradores": db.query(Ahorrador).order_by(Ahorrador.nombre).all()},
    )


@router.post("/admin/ahorradores")
def crear_ahorrador(
    request: Request,
    nombre: str = Form(...),
    documento: str = Form(...),
    area: str = Form(...),
    fecha_ingreso: str = Form(...),
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    def _error(msg):
        return templates.TemplateResponse(
            request,
            "admin_ahorradores.html",
            {"request": request, "error": msg,
             "ahorradores": db.query(Ahorrador).order_by(Ahorrador.nombre).all()},
            status_code=400,
        )

    nombre, documento, area = nombre.strip(), documento.strip(), area.strip()
    if not nombre or not documento or not area:
        return _error("Nombre, documento y área son obligatorios.")
    try:
        ingreso = date.fromisoformat(fecha_ingreso)
    except ValueError:
        return _error("Fecha de ingreso inválida (AAAA-MM-DD).")
    if db.query(Ahorrador).filter_by(documento=documento).first():
        return _error(f"Ya existe un ahorrador con documento {documento}.")
    usuario_id = None
    if username.strip():
        if db.query(Usuario).filter_by(username=username.strip()).first():
            return _error(f"El usuario {username.strip()} ya existe.")
        if not password:
            return _error("La cuenta de acceso requiere contraseña.")
        nuevo = Usuario(username=username.strip(),
                        password_hash=deps.hash_password(password), rol=ROL_AHORRADOR)
        db.add(nuevo)
        db.flush()
        usuario_id = nuevo.id
    a = Ahorrador(nombre=nombre, documento=documento, area=area,
                  fecha_ingreso=ingreso, usuario_id=usuario_id)
    db.add(a)
    db.commit()
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/admin/ahorradores", status_code=303)


@router.get("/admin/aportes", response_class=HTMLResponse)
def ver_aportes(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    return templates.TemplateResponse(
        request,
        "admin_aportes.html",
        {"request": request,
         "ahorradores": db.query(Ahorrador).order_by(Ahorrador.nombre).all(),
         "aportes": db.query(Aporte).order_by(Aporte.fecha.desc()).limit(50).all()},
    )


@router.post("/admin/aportes")
def crear_aporte(
    request: Request,
    ahorrador_id: int = Form(...),
    fecha: str = Form(...),
    monto: int = Form(...),
    comprobante: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    def _error(msg):
        return templates.TemplateResponse(
            request,
            "admin_aportes.html",
            {"request": request, "error": msg,
             "ahorradores": db.query(Ahorrador).order_by(Ahorrador.nombre).all(),
             "aportes": db.query(Aporte).order_by(Aporte.fecha.desc()).limit(50).all()},
            status_code=400,
        )

    a = db.get(Ahorrador, ahorrador_id)
    if a is None:
        return _error("Ahorrador inexistente.")
    try:
        f = date.fromisoformat(fecha)
    except ValueError:
        return _error("Fecha inválida (AAAA-MM-DD).")
    if f > _hoy():
        return _error("La fecha del aporte no puede ser futura.")
    if monto <= 0:
        return _error("El monto debe ser mayor que cero.")
    if not comprobante.strip():
        return _error("El comprobante es obligatorio.")
    db.add(Aporte(ahorrador_id=a.id, fecha=f, monto=monto,
                  comprobante=comprobante.strip(), registrado_por=user.username))
    db.commit()
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/admin/aportes", status_code=303)


@router.get("/admin/cierre", response_class=HTMLResponse)
def ver_cierre(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    ultimo = db.query(Reparto).order_by(Reparto.ciclo_ano.desc()).first()
    return templates.TemplateResponse(
        request, "admin_cierre.html", {"request": request, "reparto": ultimo},
    )


@router.post("/admin/cierre")
def hacer_cierre(
    request: Request,
    ciclo_ano: int = Form(...),
    fecha_corte: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    try:
        corte = date.fromisoformat(fecha_corte)
    except ValueError:
        return templates.TemplateResponse(
            request, "admin_cierre.html",
            {"request": request, "error": "Fecha de corte inválida (AAAA-MM-DD).",
             "reparto": db.query(Reparto).order_by(Reparto.ciclo_ano.desc()).first()},
            status_code=400,
        )
    try:
        ejecutar_reparto(db, ciclo_ano, corte, user.id)
    except ValueError as e:
        return templates.TemplateResponse(
            request, "admin_cierre.html",
            {"request": request, "error": str(e),
             "reparto": db.query(Reparto).order_by(Reparto.ciclo_ano.desc()).first()},
            status_code=400,
        )
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/admin/cierre", status_code=303)
