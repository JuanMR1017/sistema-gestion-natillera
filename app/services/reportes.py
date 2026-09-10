"""Reportes consolidados desde las consultas de vista (FR-009, HU-09).

Principio I: reporte y pantalla nunca divergen — los totales se calculan
con las mismas funciones que las vistas (`saldos`, `mora`, `finance`).
Excel vía openpyxl; PDF con generador propio mínimo (sin dependencias
nativas) con el mismo contenido tabular.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from io import BytesIO

from sqlalchemy.orm import Session

from app.models.aporte import Aporte
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo
from app.services.finance import interes_cobrado
from app.services.mora import ESTADOS_VIGENTES, dias_vencidos
from app.services.saldos import fondo_disponible, fondo_total, prestado_activo

TIPOS = ("aportes", "prestamos_activos", "mora", "fondos")


def reporte_aportes(db: Session, desde: date, hasta: date) -> dict:
    filas = (
        db.query(Aporte).filter(Aporte.fecha >= desde, Aporte.fecha <= hasta)
        .order_by(Aporte.fecha.asc(), Aporte.id.asc()).all()
    )
    return {
        "columnas": ["fecha", "ahorrador", "documento", "monto", "comprobante",
                     "registrado_por"],
        "filas": [[str(a.fecha), a.ahorrador.nombre, a.ahorrador.documento,
                   a.monto, a.comprobante, a.registrado_por] for a in filas],
        "total": sum(a.monto for a in filas),
    }


def reporte_prestamos_activos(db: Session) -> dict:
    prestamos = (
        db.query(Prestamo).filter(Prestamo.estado.in_(ESTADOS_VIGENTES))
        .order_by(Prestamo.fecha_solicitud.asc()).all()
    )
    filas = []
    for p in prestamos:
        pendientes = sorted(
            (c for c in p.cuotas if c.estado != "Pagada"),
            key=lambda c: c.fecha_vencimiento,
        )
        prox = (f"#{pendientes[0].numero} ${pendientes[0].valor} "
                f"vence {pendientes[0].fecha_vencimiento}" if pendientes else "—")
        saldo = sum(c.valor - c.abonado for c in p.cuotas)
        filas.append([p.id, p.solicitante.nombre, p.monto, p.plazo_meses,
                      p.tasa_mensual_aplicada, saldo, p.estado, prox])
    return {
        "columnas": ["prestamo", "solicitante", "monto", "plazo_meses",
                     "tasa_aplicada", "saldo_pendiente", "estado",
                     "proxima_cuota"],
        "filas": filas,
        "total": sum(f[5] for f in filas),
    }


def reporte_mora(db: Session, hoy: date | None = None) -> dict:
    hoy = hoy or datetime.now(UTC).date()
    cuotas = (
        db.query(Cuota).filter_by(estado="En mora")
        .order_by(Cuota.fecha_vencimiento.asc()).all()
    )
    filas = [[c.prestamo.solicitante.nombre, c.prestamo.solicitante.documento,
              c.prestamo_id, c.numero, c.valor,
              str(c.fecha_vencimiento),
              dias_vencidos(c.fecha_vencimiento, hoy), c.abonado]
             for c in cuotas]
    return {
        "columnas": ["ahorrador", "documento", "prestamo", "cuota", "valor",
                     "vencimiento", "dias_mora", "abonado_parcial"],
        "filas": filas,
        "total": sum(f[4] - f[7] for f in filas),
    }


def reporte_fondos(db: Session, corte: date) -> dict:
    utilidades = sum(
        interes_cobrado(c.valor, c.interes, c.abonado)
        for c in db.query(Cuota).all()
    )
    aportado = fondo_total(db)
    prestado = prestado_activo(db)
    return {
        "columnas": ["concepto", "valor"],
        "filas": [["total_aportado", aportado],
                  ["total_prestado_activo", prestado],
                  ["disponible", aportado - prestado],
                  ["total_utilidades", utilidades],
                  ["fecha_corte", str(corte)]],
        "total": aportado,
        "total_aportado": aportado,
        "prestado_activo": prestado,
        "disponible": fondo_disponible(db),
    }


def a_excel(titulo: str, reporte: dict) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = titulo[:31]
    ws.append(reporte["columnas"])
    for fila in reporte["filas"]:
        ws.append(fila)
    ws.append(["TOTAL"] + [""] * (len(reporte["columnas"]) - 2)
              + [reporte["total"]])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _latin(texto: str) -> str:
    return (texto.encode("latin-1", errors="replace").decode("latin-1")
            .replace("(", "[").replace(")", "]").replace("\\", "/"))


def a_pdf(titulo: str, reporte: dict) -> bytes:
    """PDF tabular mínimo de una o más páginas (texto, Helvetica)."""
    lineas = [_latin(titulo), "",
              _latin(" | ".join(map(str, reporte["columnas"])))]
    for fila in reporte["filas"]:
        lineas.append(_latin(" | ".join(map(str, fila))[:110]))
    lineas += ["", _latin(f"TOTAL: {reporte['total']}")]
    por_pagina, paginas = 45, []
    for i in range(0, len(lineas), por_pagina):
        paginas.append(lineas[i:i + por_pagina])

    objetos: dict[int, bytes] = {}
    ids_pagina, ids_contenido = [], []
    siguiente = 3
    for pg in paginas:
        ids_pagina.append(siguiente)
        ids_contenido.append(siguiente + 1)
        cuerpo = ["BT /F1 10 Tf 40 760 Td 12 TL"]
        for j, ln in enumerate(pg):
            cuerpo.append(f"({ln}) Tj")
            if j < len(pg) - 1:
                cuerpo.append("T*")
        cuerpo.append("ET")
        stream = "\n".join(cuerpo).encode("latin-1")
        objetos[siguiente + 1] = (
            b"<< /Length " + str(len(stream)).encode()
            + b" >>\nstream\n" + stream + b"\nendstream"
        )
        siguiente += 2
    id_fuente = siguiente
    kids = " ".join(f"{i} 0 R" for i in ids_pagina)
    objetos[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objetos[2] = (f"<< /Type /Pages /Kids [{kids}] "
                  f"/Count {len(paginas)} >>").encode()
    for pid, cid in zip(ids_pagina, ids_contenido):
        objetos[pid] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {cid} 0 R /Resources << /Font << /F1 "
            f"{id_fuente} 0 R >> >> >>"
        ).encode()
    objetos[id_fuente] = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    salida = [b"%PDF-1.4"]
    offsets = []
    for num in range(1, id_fuente + 1):
        offsets.append(sum(len(x) + 1 for x in salida))
        salida.append(f"{num} 0 obj".encode() + b"\n" + objetos[num] + b"\nendobj")
    inicio_xref = sum(len(x) + 1 for x in salida)
    n = id_fuente + 1
    xref = [f"xref\n0 {n}".encode(), b"0000000000 65535 f "]
    xref += [f"{o:010d} 00000 n ".encode() for o in offsets]
    salida += xref + [f"trailer\n<< /Size {n} /Root 1 0 R >>".encode(),
                      b"startxref", str(inicio_xref).encode(), b"%%EOF"]
    return b"\n".join(salida)
