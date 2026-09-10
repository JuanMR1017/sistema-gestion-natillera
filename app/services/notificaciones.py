"""Notificaciones in-app: registro y avisos por evento (FR-010, HU-10).

Canal base plataforma (tabla Notificacion). US6 agrega plantillas,
listado y correo SMTP; este helper ya deja trazabilidad de cada evento.
"""

from __future__ import annotations

import os
import smtplib
from datetime import UTC, date, datetime
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.models.notificacion import (
    CANAL_CORREO,
    CANAL_PLATAFORMA,
    RECORDATORIO_APORTE,
    VENCIMIENTO,
    Notificacion,
)
from app.models.usuario import ROL_ADMINISTRADOR, Usuario

# Cuotas que vencen dentro de esta ventana generan alerta (QS-6).
VENTANA_VENCIMIENTO_DIAS = int(os.environ.get("AVISO_VENCIMIENTO_DIAS", "7"))
# Días sin aportes que disparan el recordatorio periódico.
VENTANA_APORTE_DIAS = 30


def texto_solicitud(prestamo_id: int, nombre: str, monto: int, plazo: int) -> str:
    return (f"Nueva solicitud #{prestamo_id} de {nombre} por ${monto} "
            f"a {plazo} meses.")


def texto_cambio_estado(prestamo_id: int, anterior: str, nuevo: str,
                        extra: str = "") -> str:
    verbo = {"Aprobado": "fue aprobada", "Rechazado": "fue rechazada",
             "Pagado": "quedó saldada"}.get(nuevo, f"pasó a {nuevo}")
    base = (f"Tu solicitud #{prestamo_id} {verbo} "
            f"(de {anterior} a {nuevo}).")
    return f"{base} {extra}".strip()


def texto_vencimiento(prestamo_id: int, numero: int, valor: int,
                      fecha_limite: date) -> str:
    return (f"Vence tu cuota #{numero} del préstamo #{prestamo_id} por "
            f"${valor}: fecha límite {fecha_limite}.")


def texto_recordatorio(minimo: str) -> str:
    return (f"Recordatorio de aporte periódico: el monto mínimo vigente es "
            f"${minimo}. Mantén tus aportes al día para conservar tu "
            f"elegibilidad de préstamo.")


def notificar(db: Session, destinatario: str, tipo: str, detalle: str,
              canal: str = CANAL_PLATAFORMA) -> Notificacion:
    n = Notificacion(destinatario=destinatario, tipo=tipo, canal=canal,
                     detalle=detalle)
    db.add(n)
    return n


def avisar_admins(db: Session, tipo: str, detalle: str) -> int:
    """Crea un aviso por cada administrador activo. Retorna cuántos."""
    admins = db.query(Usuario).filter_by(rol=ROL_ADMINISTRADOR, activo=True).all()
    for a in admins:
        notificar(db, a.username, tipo, detalle)
    return len(admins)


def _ya_avisado(db: Session, destinatario: str, tipo: str, clave: str) -> bool:
    return (
        db.query(Notificacion)
        .filter(Notificacion.destinatario == destinatario,
                Notificacion.tipo == tipo,
                Notificacion.leida.is_(False),
                Notificacion.detalle.contains(clave))
        .count()
        > 0
    )


def generar_avisos_para_usuario(db: Session, user, hoy: date | None = None) -> list:
    """Job de avisos (vencimientos + recordatorio) para un usuario.

    Idempotente: no duplica avisos no leídos. Se ejecuta on-read al abrir
    los avisos (complemento del job programado). Retorna los creados.
    """
    from app.models.ahorrador import Ahorrador
    from app.models.aporte import Aporte
    from app.models.parametro import MONTO_MINIMO_APORTE, vigente
    from app.models.prestamo import Prestamo
    from app.services.mora import ESTADOS_VIGENTES

    hoy = hoy or datetime.now(UTC).date()
    a = db.query(Ahorrador).filter_by(usuario_id=user.id).first()
    if a is None:
        return []
    creados = []
    prestamos = (
        db.query(Prestamo).filter_by(solicitante_id=a.id)
        .filter(Prestamo.estado.in_(ESTADOS_VIGENTES)).all()
    )
    for p in prestamos:
        for c in p.cuotas:
            if c.estado == "Pagada":
                continue
            faltan = (c.fecha_vencimiento - hoy).days
            if 0 <= faltan <= VENTANA_VENCIMIENTO_DIAS:
                clave = f"préstamo #{p.id} cuota #{c.numero}"
                if not _ya_avisado(db, user.username, VENCIMIENTO, clave):
                    creados.append(notificar(
                        db, user.username, VENCIMIENTO,
                        f"Vence tu cuota #{c.numero} del préstamo #{p.id} "
                        f"por ${c.valor}: fecha límite {c.fecha_vencimiento}."))
    ultimo = (
        db.query(Aporte).filter_by(ahorrador_id=a.id)
        .order_by(Aporte.fecha.desc()).first()
    )
    if ((ultimo is None or (hoy - ultimo.fecha).days > VENTANA_APORTE_DIAS)
            and not _ya_avisado(db, user.username, RECORDATORIO_APORTE, "aporte")):
        minimo = vigente(db, MONTO_MINIMO_APORTE)
        creados.append(notificar(db, user.username, RECORDATORIO_APORTE,
                                 texto_recordatorio(minimo)))
    if creados:
        db.commit()
    return creados


def enviar_pendientes_por_correo(db: Session, limite: int = 50) -> int:
    """Intenta enviar por SMTP los avisos de canal correo.

    Sin SMTP_HOST configurado retorna 0 sin errores (plataforma sigue
    siendo el canal base garantizado).
    """
    host = os.environ.get("SMTP_HOST")
    if not host:
        return 0
    pendientes = (
        db.query(Notificacion).filter_by(canal=CANAL_CORREO, leida=False)
        .order_by(Notificacion.id.asc()).limit(limite).all()
    )
    enviados = 0
    for n in pendientes:
        try:
            msg = EmailMessage()
            msg["Subject"] = f"[Natillera] {n.tipo}"
            msg["From"] = os.environ.get("SMTP_FROM", "natillera@example.com")
            msg["To"] = n.destinatario
            msg.set_content(n.detalle)
            with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "25")),
                              timeout=10) as s:
                smtp_user = os.environ.get("SMTP_USER")
                if smtp_user:
                    s.login(smtp_user, os.environ.get("SMTP_PASS", ""))
                s.send_message(msg)
            n.leida = True
            enviados += 1
        except (OSError, smtplib.SMTPException):
            continue
    if enviados:
        db.commit()
    return enviados
