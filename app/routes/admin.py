"""Panel de administración: índice, ahorradores, aportes, préstamos y cierre
(FR-002, FR-003, FR-005, FR-006, FR-011)."""

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
from app.models.cuota import Cuota
from app.models.notificacion import CAMBIO_ESTADO
from app.models.parametro import TASA_MENSUAL, vigente
from app.models.prestamo import APROBADO, PAGADO, PENDIENTE, RECHAZADO, Prestamo
from app.models.reparto import Reparto
from app.models.usuario import ROL_ADMINISTRADOR, ROL_AHORRADOR, Usuario
from app.services import reportes as svc_reportes
from app.services.finance import imputar_pago, tabla_cuotas
from app.services.mora import ESTADOS_VIGENTES, evaluar_mora, saldo_pendiente
from app.services.notificaciones import notificar, texto_cambio_estado
from app.services.reparto import ejecutar_reparto
from app.services.saldos import fondo_disponible, fondo_total, prestado_activo

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
        {"request": request, "total_usuarios": db.query(Usuario).count(),
         "total_ahorradores": db.query(Ahorrador).count(),
         "fondo_total": fondo_total(db),
         "prestado": prestado_activo(db),
         "disponible": fondo_disponible(db),
         "pendientes": db.query(Prestamo).filter_by(estado=PENDIENTE).count(),
         "vigentes": db.query(Prestamo).filter(
             Prestamo.estado.in_(ESTADOS_VIGENTES)).count(),
         "en_mora": db.query(Cuota).filter_by(estado="En mora").count()},
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


@router.post("/admin/ahorradores/{ahorrador_id}/editar")
def editar_ahorrador(
    request: Request,
    ahorrador_id: int,
    nombre: str = Form(...),
    area: str = Form(...),
    fecha_ingreso: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    a = db.get(Ahorrador, ahorrador_id)
    if a is None:
        return templates.TemplateResponse(
            request, "admin_ahorradores.html",
            {"request": request, "error": "Ahorrador inexistente.",
             "ahorradores": db.query(Ahorrador).all()}, status_code=404)
    nombre, area = nombre.strip(), area.strip()
    if not nombre or not area:
        return templates.TemplateResponse(
            request, "admin_ahorradores.html",
            {"request": request, "error": "Nombre y área son obligatorios.",
             "ahorradores": db.query(Ahorrador).all()}, status_code=400)
    try:
        a.fecha_ingreso = date.fromisoformat(fecha_ingreso)
    except ValueError:
        return templates.TemplateResponse(
            request, "admin_ahorradores.html",
            {"request": request, "error": "Fecha de ingreso inválida.",
             "ahorradores": db.query(Ahorrador).all()}, status_code=400)
    # Documento inmutable: es la llave del historial (FR-002).
    a.nombre, a.area = nombre, area
    db.commit()
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/admin/ahorradores", status_code=303)


@router.post("/admin/ahorradores/{ahorrador_id}/baja")
def baja_ahorrador(
    request: Request,
    ahorrador_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    from app.services.saldos import saldo_acumulado

    a = db.get(Ahorrador, ahorrador_id)
    if a is None:
        return templates.TemplateResponse(
            request, "admin_ahorradores.html",
            {"request": request, "error": "Ahorrador inexistente.",
             "ahorradores": db.query(Ahorrador).all()}, status_code=404)

    def _error(msg):
        return templates.TemplateResponse(
            request, "admin_ahorradores.html",
            {"request": request, "error": msg,
             "ahorradores": db.query(Ahorrador).order_by(Ahorrador.nombre).all()},
            status_code=400,
        )

    if not a.activo:
        return _error("El ahorrador ya está inactivo.")
    saldo = saldo_acumulado(db, a.id)
    if saldo > 0:
        return _error(f"La baja está bloqueada: el ahorrador tiene saldo "
                      f"${saldo}. Liquide primero (retiro por excepción RN-07).")
    abiertos = (
        db.query(Prestamo).filter_by(solicitante_id=a.id)
        .filter(Prestamo.estado.in_((PENDIENTE,) + ESTADOS_VIGENTES)).count()
    )
    if abiertos:
        return _error("La baja está bloqueada: el ahorrador tiene préstamos "
                      "vigentes o solicitudes pendientes.")
    # Baja lógica: nunca se elimina historial (edge case spec).
    a.activo = False
    if a.usuario is not None:
        a.usuario.activo = False
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
    if not a.activo:
        return _error("El ahorrador está inactivo; no recibe aportes.")
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


@router.get("/admin/prestamos", response_class=HTMLResponse)
def ver_prestamos(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    evaluar_mora(db)
    pendientes = (
        db.query(Prestamo).filter_by(estado=PENDIENTE)
        .order_by(Prestamo.fecha_solicitud.asc()).all()
    )
    otros = (
        db.query(Prestamo).filter(Prestamo.estado != PENDIENTE)
        .order_by(Prestamo.fecha_solicitud.desc()).limit(50).all()
    )
    return templates.TemplateResponse(
        request, "admin_prestamos.html",
        {"request": request, "pendientes": pendientes, "otros": otros},
    )


def _prestamo_para_decision(db: Session, prestamo_id: int):
    return db.get(Prestamo, prestamo_id)


@router.post("/admin/prestamos/{prestamo_id}/aprobar")
def aprobar_prestamo(
    request: Request,
    prestamo_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    def _error(msg, codigo=400):
        return templates.TemplateResponse(
            request, "admin_prestamos.html",
            {"request": request, "error": msg,
             "pendientes": db.query(Prestamo).filter_by(estado=PENDIENTE)
             .order_by(Prestamo.fecha_solicitud.asc()).all(),
             "otros": []},
            status_code=codigo,
        )

    p = _prestamo_para_decision(db, prestamo_id)
    if p is None:
        return _error("Solicitud inexistente.", 404)
    evaluar_mora(db)
    db.refresh(p)
    if p.estado != PENDIENTE:
        # Aprobación atómica: la segunda decisión concurrente ve el estado
        # actualizado sin efecto duplicado (edge case spec).
        return _error(f"La solicitud #{p.id} ya fue procesada "
                      f"(estado actual: {p.estado}).", 409)
    if p.monto > fondo_disponible(db):
        return _error(f"Liquidez insuficiente: disponible "
                      f"${fondo_disponible(db)} para ${p.monto}.")
    tasa = float(vigente(db, TASA_MENSUAL))
    hoy = datetime.now(UTC).date()
    p.tasa_mensual_aplicada = tasa
    p.estado = APROBADO
    p.aprobado_por = user.username
    p.fecha_aprobacion = hoy
    for fila in tabla_cuotas(p.monto, tasa, p.plazo_meses, hoy):
        db.add(Cuota(prestamo_id=p.id, numero=fila["numero"], valor=fila["valor"],
                     capital=fila["capital"], interes=fila["interes"],
                     fecha_vencimiento=fila["fecha_vencimiento"],
                     abonado=0, estado="Pendiente"))
    solicitante = db.get(Ahorrador, p.solicitante_id)
    destino = solicitante.usuario.username if solicitante and solicitante.usuario else None
    if destino:
        notificar(db, destino, "cambio_estado",
                  texto_cambio_estado(p.id, PENDIENTE, APROBADO,
                                      f"Monto ${p.monto} a {p.plazo_meses} meses."))
    db.commit()
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/admin/prestamos", status_code=303)


@router.post("/admin/prestamos/{prestamo_id}/rechazar")
def rechazar_prestamo(
    request: Request,
    prestamo_id: int,
    motivo: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    def _error(msg, codigo=400):
        return templates.TemplateResponse(
            request, "admin_prestamos.html",
            {"request": request, "error": msg,
             "pendientes": db.query(Prestamo).filter_by(estado=PENDIENTE)
             .order_by(Prestamo.fecha_solicitud.asc()).all(),
             "otros": []},
            status_code=codigo,
        )

    p = _prestamo_para_decision(db, prestamo_id)
    if p is None:
        return _error("Solicitud inexistente.", 404)
    if p.estado != PENDIENTE:
        return _error(f"La solicitud #{p.id} ya fue procesada "
                      f"(estado actual: {p.estado}).", 409)
    motivo = motivo.strip()
    if not motivo:
        return _error("El motivo del rechazo es obligatorio.")
    p.estado = RECHAZADO
    p.motivo_rechazo = motivo[:280]
    p.aprobado_por = user.username
    solicitante = db.get(Ahorrador, p.solicitante_id)
    destino = solicitante.usuario.username if solicitante and solicitante.usuario else None
    if destino:
        notificar(db, destino, "cambio_estado",
                  texto_cambio_estado(p.id, PENDIENTE, RECHAZADO, motivo[:200]))
    db.commit()
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/admin/prestamos", status_code=303)


@router.get("/admin/cartera", response_class=HTMLResponse)
def ver_cartera(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    evaluar_mora(db)
    prestamos = (
        db.query(Prestamo).filter(Prestamo.estado.in_(ESTADOS_VIGENTES))
        .order_by(Prestamo.fecha_solicitud.asc()).all()
    )
    return templates.TemplateResponse(
        request, "cartera.html",
        {"request": request, "prestamos": prestamos,
         "saldo_pendiente": saldo_pendiente},
    )


@router.post("/admin/pagos")
def registrar_pago(
    request: Request,
    cuota_id: int = Form(...),
    valor: int = Form(...),
    fecha: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    def _error(msg, codigo=400):
        evaluar_mora(db)
        prestamos = (
            db.query(Prestamo).filter(Prestamo.estado.in_(ESTADOS_VIGENTES))
            .order_by(Prestamo.fecha_solicitud.asc()).all()
        )
        return templates.TemplateResponse(
            request, "cartera.html",
            {"request": request, "error": msg, "prestamos": prestamos,
             "saldo_pendiente": saldo_pendiente},
            status_code=codigo,
        )

    c = db.get(Cuota, cuota_id)
    if c is None:
        return _error("Cuota inexistente.", 404)
    try:
        f = date.fromisoformat(fecha)
    except ValueError:
        return _error("Fecha inválida (AAAA-MM-DD).")
    if f > _hoy():
        return _error("La fecha del abono no puede ser futura.")
    if valor <= 0:
        return _error("El abono debe ser mayor que cero.")
    evaluar_mora(db)
    db.refresh(c)
    if c.estado == "Pagada":
        return _error(f"La cuota #{c.numero} ya está pagada.")
    remanente = c.valor - c.abonado
    if valor > remanente:
        return _error(f"El abono ${valor} excede el remanente ${remanente}.")
    _, _, nuevo, estado = imputar_pago(c.valor, c.capital, c.interes,
                                       c.abonado, valor)
    c.abonado, c.estado = nuevo, estado
    p = c.prestamo
    if p.cuotas and all(c2.estado == "Pagada" for c2 in p.cuotas):
        previo = p.estado
        p.estado = PAGADO
        destino = (p.solicitante.usuario.username
                   if p.solicitante and p.solicitante.usuario else None)
        if destino:
            notificar(db, destino, CAMBIO_ESTADO,
                      texto_cambio_estado(p.id, previo, PAGADO,
                                          "¡Gracias por tu pago!"))
    else:
        evaluar_mora(db)
    db.commit()
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/admin/cartera", status_code=303)


@router.get("/admin/parametros", response_class=HTMLResponse)
def ver_parametros(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    from app.models.parametro import Parametro

    return templates.TemplateResponse(
        request, "admin_parametros.html",
        {"request": request,
         "parametros": db.query(Parametro).order_by(
             Parametro.clave.asc(), Parametro.vigente_desde.desc()).all()},
    )


def _validar_parametro(clave: str, valor: str) -> str | None:
    """Retorna mensaje de error o None si el valor es válido (FR-012)."""
    from app.models.parametro import (
        DIAS_GRACIA_MORA,
        MONTO_MINIMO_APORTE,
        TASA_MENSUAL,
        TOPE_PORCENTAJE_SALDO,
    )

    try:
        numero = float(valor)
    except ValueError:
        return "El valor debe ser numérico."
    if clave == TASA_MENSUAL and not 0 < numero <= 1:
        return "La tasa mensual debe estar entre 0 y 1 (ej. 0.015)."
    if clave == TOPE_PORCENTAJE_SALDO and not 0 < numero <= 100:
        return "El tope debe estar entre 0 y 100 (porcentaje)."
    if (clave in (MONTO_MINIMO_APORTE, DIAS_GRACIA_MORA)
            and (numero < 0 or not numero.is_integer())):
        return "El valor debe ser un entero mayor o igual a cero."
    return None


@router.post("/admin/parametros")
def cambiar_parametro(
    request: Request,
    clave: str = Form(...),
    valor: str = Form(...),
    vigente_desde: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    from datetime import timedelta

    from app.models.parametro import Parametro

    def _error(msg, codigo=400):
        return templates.TemplateResponse(
            request, "admin_parametros.html",
            {"request": request, "error": msg,
             "parametros": db.query(Parametro).order_by(
                 Parametro.clave.asc(), Parametro.vigente_desde.desc()).all()},
            status_code=codigo,
        )

    actual = (
        db.query(Parametro).filter_by(clave=clave, vigente_hasta=None)
        .order_by(Parametro.vigente_desde.desc()).first()
    )
    if actual is None:
        return _error("Parámetro desconocido.", 404)
    if (msg := _validar_parametro(clave, valor)) is not None:
        return _error(msg)
    try:
        desde = date.fromisoformat(vigente_desde)
    except ValueError:
        return _error("Vigencia inválida (AAAA-MM-DD).")
    if desde <= actual.vigente_desde:
        return _error("La nueva vigencia debe ser posterior a la actual.")
    # Cierre versionado: nunca se edita destructivamente (FR-012).
    actual.vigente_hasta = desde - timedelta(days=1)
    db.add(Parametro(clave=clave, valor=valor.strip(), vigente_desde=desde,
                     vigente_hasta=None, modificado_por=user.username))
    db.commit()
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/admin/parametros", status_code=303)


@router.get("/admin/reportes", response_class=HTMLResponse)
def ver_reportes(
    request: Request,
    tipo: str = "aportes",
    desde: str = "2026-01-01",
    hasta: str = "",
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    from app.services.reportes import TIPOS

    if not hasta:
        hasta = _hoy().isoformat()
    try:
        d1, d2 = date.fromisoformat(desde), date.fromisoformat(hasta)
    except ValueError:
        return templates.TemplateResponse(
            request, "reportes.html",
            {"request": request, "error": "Rango de fechas inválido (AAAA-MM-DD).",
             "tipos": TIPOS, "tipo": tipo, "desde": desde, "hasta": hasta,
             "reporte": None},
            status_code=400,
        )
    if tipo not in TIPOS:
        tipo = "aportes"
    reporte = _generar_reporte(db, tipo, d1, d2)
    return templates.TemplateResponse(
        request, "reportes.html",
        {"request": request, "tipos": list(TIPOS), "tipo": tipo,
         "desde": desde, "hasta": hasta, "reporte": reporte},
    )


def _generar_reporte(db: Session, tipo: str, d1: date, d2: date) -> dict:
    evaluar_mora(db)
    if tipo == "aportes":
        return svc_reportes.reporte_aportes(db, d1, d2)
    if tipo == "prestamos_activos":
        return svc_reportes.reporte_prestamos_activos(db)
    if tipo == "mora":
        return svc_reportes.reporte_mora(db)
    return svc_reportes.reporte_fondos(db, d2)


@router.get("/admin/reportes/descargar")
def descargar_reporte(
    tipo: str = "aportes",
    desde: str = "2026-01-01",
    hasta: str = "",
    formato: str = "xlsx",
    db: Session = Depends(get_db),
    user=Depends(require_role(ROL_ADMINISTRADOR)),
):
    from fastapi.responses import Response

    from app.services.reportes import TIPOS

    if not hasta:
        hasta = _hoy().isoformat()
    try:
        d1, d2 = date.fromisoformat(desde), date.fromisoformat(hasta)
    except ValueError:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Rango inválido.")
    if tipo not in TIPOS:
        tipo = "aportes"
    reporte = _generar_reporte(db, tipo, d1, d2)
    nombre = f"reporte_{tipo}_{d1}_{d2}"
    if formato == "pdf":
        contenido = svc_reportes.a_pdf(f"Reporte {tipo}", reporte)
        return Response(contenido, media_type="application/pdf",
                        headers={"Content-Disposition":
                                 f'attachment; filename="{nombre}.pdf"'})
    contenido = svc_reportes.a_excel(f"Reporte {tipo}", reporte)
    return Response(
        contenido,
        media_type="application/vnd.openxmlformats-officedocument"
                   ".spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}.xlsx"'})



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
