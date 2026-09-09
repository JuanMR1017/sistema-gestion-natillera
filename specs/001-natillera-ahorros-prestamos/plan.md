# Implementation Plan: Sistema de Gestión de Natillera (Ahorros y Préstamos)

**Branch**: `001-natillera-ahorros-prestamos` | **Date**: 2026-09-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-natillera-ahorros-prestamos/spec.md`

## Summary

Sistema web que automatiza la natillera (ahorradores, aportes, préstamos, pagos,
reportes, notificaciones, reparto anual) eliminando cuadernos y mensajería.
Enfoque técnico (ver `research.md`): monolito server-render Python 3.13 + FastAPI +
Jinja2/htmx, PostgreSQL (prod) / SQLite (dev) tras repositorios, motor financiero
único y versionado, sesiones con bcrypt, alertas internas + SMTP, Excel/PDF desde las
mismas consultas de vista, pytest + pytest-bdd con los Gherkin HU-01–HU-10.

## Technical Context

**Language/Version**: Python 3.13 (constitución exige 3.11+; entorno verificado 3.13.6)

**Primary Dependencies**: FastAPI, Jinja2, htmx, SQLAlchemy (repositorios), openpyxl
(Excel), WeasyPrint (PDF), bcrypt (hash), pytest + pytest-bdd + TestClient (tests)

**Storage**: PostgreSQL en producción con `pg_dump` diario (retención 30 días);
SQLite en desarrollo/pruebas; respaldos automáticos programados (RNF-08)

**Testing**: pytest + TestClient + pytest-bdd (aceptación HU-01–HU-10); unitarias al
motor (ancla $500k/12m ≈ $46.701); prueba de carga 200+ ahorradores (SC-011)

**Target Platform**: Servidor Linux desplegable, desarrollo en Windows; navegadores
Chrome/Edge/Firefox + móvil responsive (RNF-02, RNF-06)

**Project Type**: web application (monolito server-render, sin SPA)

**Performance Goals**: Consultas de saldo y solicitudes < 3 s (RNF-04); reportes y
consultas con 200+ ahorradores dentro de los mismos umbrales (SC-011)

**Constraints**: COP enteros sin decimales (redondeo mitad arriba); Ley 1581
(minimización, visibilidad privada por defecto); movimientos append-only; fuera de
alcance pasarelas de pago y declaraciones tributarias (FR-014)

**Scale/Scope**: 200+ ahorradores registrados; ~10 rutas de página + 12 acciones POST;
3 vistas estratégicas (dashboard, solicitud, admin); 7 user stories (R1 MVP → R3 cierre)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Trazabilidad**: movimientos append-only con actor/fecha/monto/evidencia
  (`data-model.md`: Aporte, Cuota, Reparto); saldos derivados; reportes desde las
  mismas consultas que las vistas. Sin ajustes manuales.
- [x] **II. Cálculos auditables**: motor único versionado (`research.md` R-04) con
  tasa, tope, mínimo y gracia parametrizados; test ancla $500k/12m; recálculo tras
  cada abono con estados Pagada/Parcial derivados.
- [x] **III. Roles + Ley 1581**: sesiones bcrypt, deny-by-default, aprobación exclusiva
  admin (RN-06), bloqueo automático por mora (RN-04), visibilidad privada por defecto
  (clarify A), backups programados (R-02).
- [x] **IV. Test-first Gherkin**: HU-01–HU-10 como aceptación pytest-bdd; QS-1–QS-8 en
  `quickstart.md`; Red-Green-Refactor antes de implementar.
- [x] **V. Simplicidad y rendimiento**: server-render sin SPA (YAGNI), 3 vistas Figma,
  < 3 s, ≥ 95% disponibilidad en fechas operativas, modular para 200+ usuarios.

**Re-evaluación post-Fase 1**: PASS — ningún artefacto introduce violaciones; sin
excepciones que justificar (ver Complexity Tracking vacío).

## Project Structure

### Documentation (this feature)

```text
specs/001-natillera-ahorros-prestamos/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── routes.md        # Páginas y acciones (contratos UI)
│   └── exports.md       # Reportes, reparto y notificaciones
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
app/
├── main.py            # App FastAPI, montaje de rutas
├── deps.py            # Sesión, auth por roles, DB session
├── models/            # Usuario, Ahorrador, Aporte, Prestamo, Cuota, Parametro, Notificacion, Reparto
├── services/          # finance.py (motor), mora.py, reparto.py, reportes.py, notificaciones.py, backups.py
├── routes/            # auth.py, ahorrador.py, admin.py (ahorradores, aportes, prestamos, pagos, reportes, cierre)
├── templates/         # base + dashboard, solicitud_prestamo, admin (+ parciales htmx)
└── static/            # css (azul marino/blanco responsive), js mínimo

tests/
├── acceptance/        # pytest-bdd: HU-01..HU-10 (Gherkin del Entregable #1)
├── integration/       # flujos: solicitud→aprobación→pago→reparto; concurrencia de aprobación
└── unit/              # motor financiero (ancla $500k/12m), mora automática, reparto proporcional
```

**Structure Decision**: Monolito web server-render (una sola app desplegable). Sin
frontend separado: las plantillas Jinja viven en `app/templates` porque el spec solo
requiere 3 vistas y el principio V prohíbe la complejidad de una SPA. Repositorios
entre servicios y SQL para cumplir trazabilidad testeable y cambio SQLite↔PostgreSQL.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Sin violaciones — no se registran excepciones. El patrón repositorio no cuenta como
violación: es la implementación directa del principio I (trazabilidad testeable) y II
(motor único), no complejidad adicional.
