# Sistema de Gestión de Natillera (Ahorros y Préstamos)

Aplicación web que automatiza la natillera: ahorradores y aportes periódicos,
solicitud/evaluación/aprobación de préstamos internos, cálculo de intereses y
cuotas, pagos con mora automática, reportes exportables, notificaciones y
reparto anual proporcional. Monolito server-render Python + FastAPI + Jinja2.

## Requisitos

- Python 3.13+ · PostgreSQL (prod) o SQLite (dev/pruebas)

## Puesta en marcha (dev)

```bash
pip install -e ".[dev]"  # o: pip install fastapi "uvicorn[standard]" jinja2 sqlalchemy bcrypt python-multipart itsdangerous pytest pytest-bdd httpx openpyxl
python scripts/seed.py   # cuenta admin + parámetros iniciales
uvicorn app.main:app --reload
```

Abrir `/login`. Variables de entorno: `DATABASE_URL` (defecto
`sqlite:///./natillera.db`), `SECRET_KEY`, `SESSION_MAX_AGE` (segundos, 12 h),
`SMTP_HOST/PORT/USER/PASS/FROM` (correo opcional), `BACKUP_DIR`,
`AVISO_VENCIMIENTO_DIAS` (defecto 7).

## Roles

- **Ahorrador** (`/`): saldo, historial propio, solicitar préstamo
  (`/prestamos`), mis avisos (`/notificaciones`). Solo ve lo propio (Ley 1581).
- **Administrador** (`/admin`): ahorradores, aportes, préstamos
  (aprobar/rechazar), cartera y pagos, reportes Excel/PDF, parámetros
  versionados y cierre anual. Acceso cruzado → 403.

## Parámetros versionados (FR-012)

`/admin/parametros`: `tasa_mensual` (0–1), `tope_porcentaje_saldo` (0–100),
`monto_minimo_aporte` (≥ 0), `dias_gracia_mora` (≥ 0, defecto 5). Cada cambio
cierra la vigencia anterior y abre una nueva con autor; los préstamos guardan
snapshot de la tasa. Tope de préstamo = menor entre % del saldo y disponible
del fondo; mora automática al superar la gracia; bloqueo RN-04 hasta ponerse
al día.

## Pruebas

```bash
python -m pytest tests/ -q
```

Aceptación Gherkin HU-01–HU-10, integración (roles, reportes, carga 200+,
seguridad, navegación QS) y unitarias (motor ancla $500.000/12m → $46.701,
mora, reparto). Fuera de alcance: pasarelas de pago y declaraciones
tributarias (FR-014).

## Estado de implementación (2026-09-10)

Historias US1–US7 completas y verificadas: **55 tests en verde** (`pytest tests/`),
`ruff check` limpio, QA end-to-end en navegador (QS-1–QS-8) con capturas.

- **US1 auth**: login por roles, error genérico, 403 por rol, rate-limit
  (20 fallos/5 min → 429), sesiones firmadas con expiración 12 h.
- **US2 ahorradores/aportes**: CRUD con documento único, edición, baja lógica
  bloqueada con saldo o préstamos vigentes (sin borrar historial), aportes
  append-only, dashboard con saldo derivado e historial.
- **US3 préstamos**: solicitud con tope `min(% saldo, disponible)` y bloqueo
  por mora; aprobación/rechazo atómico con liquidez y tabla de cuotas del
  motor único; estimada server-side en el formulario.
- **US4 pagos/mora**: abonos total/parcial vía `imputar_pago`, recálculo de
  saldo, mora automática por días de gracia (def. 5) con levantamiento RN-04
  al ponerse al día; vista de cartera.
- **US5 reportes**: aportes, préstamos activos, mora y fondos con filtros por
  fecha; descarga Excel (openpyxl) y PDF (generador propio, mismo contenido);
  rango vacío → ceros.
- **US6 notificaciones**: avisos in-app por solicitud, cambio de estado,
  vencimiento próximo (7 días) y recordatorio de aporte (30 días),
  idempotentes; correo SMTP opcional.
- **US7 reparto**: cierre diciembre proporcional que cuadra al peso, cartera
  activa separada, préstamos saldados → Cerrados.
- **Transversal**: parámetros versionados con auditoría (`/admin/parametros`),
  panel admin con métricas, despachador `/` por rol, README y prueba de carga
  220 ahorradores < 3 s.
- **UI**: lenguaje del prototipo Figma Make (navy + tarjeta azul, tab bar
  móvil, hoja amplia admin). Ver `specs/001-natillera-ahorros-prestamos/`.

## Pendiente operativo (no código de negocio)

- Scheduler diario (mora/avisos/backups: hoy on-read + `run_backup()` manual).
- SMTP real por configurar (`SMTP_HOST/...`); rate-limit en memoria por proceso.
- Sin migraciones: BDs SQLite previas deben recrearse (`seed.py`).
- Métricas no-code SC-001/SC-004/SC-008 requieren demo y medición real.
