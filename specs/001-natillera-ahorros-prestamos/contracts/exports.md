# Contracts: Exportaciones y notificaciones

**Feature**: `specs/001-natillera-ahorros-prestamos/spec.md` · **Date**: 2026-09-09
Generados desde las mismas consultas que las vistas (principio I: reporte y pantalla
nunca divergen).

## Reportes descargables (HU-09, FR-009)

Filtros comunes: tipo (aportes | prestamos_activos | mora | fondos), desde, hasta.
Formatos: Excel (.xlsx, openpyxl) y PDF (WeasyPrint), mismo contenido tabular.

- **aportes**: columnas fecha, ahorrador (nombre + documento), monto, comprobante,
  registrado_por; fila de total. Rango sin movimientos → tabla vacía con totales en cero.
- **prestamos_activos**: préstamo, solicitante, monto, plazo, tasa aplicada,
  saldo_pendiente, estado, próxima_cuota (valor + vencimiento).
- **mora**: ahorrador, cuota (préstamo + número), valor, vencimiento, días_mora,
 abonado_parcial.
- **fondos**: total_aportado, total_prestado_activo, disponible, total_utilidades,
  fecha_corte.

## Reparto anual (HU-04, FR-011)

Documento consolidado + detalle por integrante: ahorro_aportado,
utilidad_proporcional, total_a_entregar; pie con totales que cuadran con el fondo y
cartera pendiente separada (no disponible).

## Notificaciones (HU-10, FR-010)

- **vencimiento**: destinatario, cuota (préstamo + número), valor, fecha_límite.
- **cambio_estado**: solicitud, estado anterior → nuevo, fecha, actor.
- **recordatorio_aporte**: período, monto mínimo vigente, fecha esperada.
- Canales: alerta en plataforma (base) + correo SMTP configurable (complemento).
