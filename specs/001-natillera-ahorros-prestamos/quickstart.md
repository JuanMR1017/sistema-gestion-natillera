# Quickstart: validación end-to-end de la Natillera

**Feature**: `specs/001-natillera-ahorros-prestamos/spec.md` · **Date**: 2026-09-09
Guía de ejecución y validación (sin código de implementación). Referencias:
`data-model.md`, `contracts/routes.md`, `contracts/exports.md`.

## Prerrequisitos

- Python 3.13+, `uv`, PostgreSQL (prod) o SQLite (dev/pruebas).
- Dependencias instaladas y migraciones aplicadas (ver `tasks.md` en su momento).
- Parámetros iniciales cargados: tasa mensual, tope 80%, monto mínimo, 5 días de gracia.

## Puesta en marcha

1. Iniciar la app y abrir `/login`.
2. Ingresar como Administrador (cuenta seed) → ver `GET /admin` con fondo en cero.
3. Ejecutar la suite de aceptación: pruebas Gherkin HU-01–HU-10 en verde.

## Escenarios de validación

- **QS-1 Auth y roles (US1)**: login ahorrador → su panel; login admin → panel admin;
  credenciales malas → error genérico; ahorrador en ruta admin → 403.
- **QS-2 Ahorradores y aportes (US2)**: crear ahorrador (saldo cero) → 2 aportes →
  dashboard muestra saldo exacto e historial ordenado; fondo total incluye ambos una vez.
- **QS-3 Préstamos (US3)**: solicitar (monto/plazo/motivo) → Pendiente + aviso admin →
  aprobar → tabla de cuotas; caso ancla $500.000/12m ≈ $46.701/mes visible.
  Negativos: sobre tope → bloqueo con mensaje; en mora → bloqueo.
- **QS-4 Pagos (US4)**: abono total → cuota Pagada y saldo recalculado; abono parcial →
  Parcial con remanente; cuota vencida + 5 días → mora automática y aparece en mora.
- **QS-5 Reportes (US5)**: generar aportes/préstamos/mora/fondos por rango → totales
  correctos y descarga Excel + PDF; rango vacío → ceros sin error.
- **QS-6 Notificaciones (US6)**: vencimiento próximo y cambio de estado generan alerta
  con detalle; recordatorio de aporte en fecha.
- **QS-7 Reparto (US7)**: con datos conocidos, ejecutar cierre → por integrante
  ahorro + utilidad proporcional; suma cuadra con fondo; cartera activa separada.
- **QS-8 Carga (SC-011)**: 200+ ahorradores con movimientos → consultas y reportes
  dentro de umbrales (< 3 s).

## Resultado esperado

Todos los QS en verde, 0 ajustes manuales fuera del sistema y trazabilidad completa
(actor, fecha, monto, evidencia) en cada monto visible.
