# Contracts: Rutas y acciones (app server-render)

**Feature**: `specs/001-natillera-ahorros-prestamos/spec.md` · **Date**: 2026-09-09
La interfaz del sistema son páginas y acciones de formulario (una sola fuente con los
reportes). Convenciones: sesión requerida en todo salvo login; rol indicado por ruta;
errores de validación devuelven la página con mensaje; cambios de estado solo vía POST.

## Auth (todos)

- `GET /login` → formulario de ingreso.
- `POST /login` (usuario, contraseña) → panel según rol; credenciales inválidas →
  mismo formulario con error genérico (HU-05, FR-001).
- `POST /logout` → cierra sesión.

## Ahorrador (rol Ahorrador)

- `GET /` → Dashboard: saldo acumulado, meta del ciclo, accesos rápidos, movimientos
  recientes (solo propios). Sin totales globales ni datos de terceros (clarify A).
- `GET /prestamos/nuevo` → formulario (monto, plazo_meses, motivo) con cálculo
  estimado de cuota en vivo.
- `POST /prestamos` → crea solicitud Pendiente (valida tope y mora, FR-005) y
  notifica al admin; bloqueada en mora con mensaje del tope aplicable.
- `GET /prestamos` → mis solicitudes y préstamos con estados y tabla de cuotas.
- `GET /notificaciones` → mis avisos (vencimientos, cambios de estado, recordatorios).

## Administración (rol Administrador)

- `GET /admin` → Panel: fondo total disponible, desglose prestado/disponible,
  conteos (ahorradores, préstamos activos, pendientes, en mora), tarjetas
  aprobar/rechazar.
- `GET /admin/ahorradores` + `POST /admin/ahorradores` → CRUD (HU-06, FR-002);
  documento único; baja bloqueada con saldo o préstamos activos.
- `GET /admin/aportes` + `POST /admin/aportes` (ahorrador, fecha, monto,
  comprobante) → registra aporte, actualiza saldos, confirma (HU-01, FR-003).
- `POST /admin/prestamos/{id}/aprobar` → verifica liquidez, genera cuotas, notifica
  (HU-03, FR-006). `POST /admin/prestamos/{id}/rechazar` (motivo) → notifica.
- `GET /admin/cartera` → préstamos activos, cuotas y mora (flag automático).
- `POST /admin/pagos` (préstamo/cuota, valor, fecha) → descuenta capital, recalcula,
  marca Pagada/Parcial (HU-08, FR-008).
- `GET /admin/reportes` (tipo, desde, hasta) → consolida y ofrece descarga PDF/Excel
  (HU-09, FR-009; formatos en `exports.md`).
- `GET /admin/parametros` + `POST /admin/parametros` → edita parámetros versionados
  (FR-012).
- `POST /admin/cierre` → ejecuta reparto anual a corte diciembre con detalle por
  integrante (HU-04, FR-011); marca préstamos saldados como Cerrados.

## Reglas transversales

- Toda ruta de escritura exige rol autorizado; acceso cruzado → 403 sin filtrar datos.
- Todo monto mostrado proviene de un movimiento registrado (principio I).
- Concurrencia: aprobar una solicitud Pendiente es atómico; la segunda aprobación
  concurrente recibe estado actualizado sin efecto duplicado.
