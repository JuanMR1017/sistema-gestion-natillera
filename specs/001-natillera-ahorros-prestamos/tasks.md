# Tasks: Sistema de Gestión de Natillera (Ahorros y Préstamos)

**Input**: Design documents from `/specs/001-natillera-ahorros-prestamos/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Sí — exigidos por la constitución (principio IV test-first) y el spec (Gherkin
HU-01–HU-10 en verde). Cada story escribe sus pruebas PRIMERO y verifica que FALLEN
antes de implementar.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Estructura monolito server-render según plan.md: `app/` (main, deps, models, services,
routes, templates, static) y `tests/` (acceptance, integration, unit) en la raíz.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create app/ and tests/ directory structure per plan.md (app/models, app/services, app/routes, app/templates, app/static, tests/acceptance, tests/integration, tests/unit)
- [X] T002 Initialize Python 3.13 project with FastAPI, Jinja2, SQLAlchemy, pytest dependencies in pyproject.toml
- [X] T003 [P] Configure linting and formatting (ruff) in pyproject.toml
- [X] T004 [P] Create base Jinja layout and responsive CSS (azul marino/blanco) in app/templates/base.html and app/static/css/main.css
- [X] T005 [P] Configure environment-based settings (database URL, SMTP, secrets) in app/deps.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Setup database engine/session and schema creation (PostgreSQL prod / SQLite dev) in app/deps.py
- [X] T007 [P] Create Usuario model ("nombre de usuario (único)", "hash de contraseña (bcrypt)", "rol (Ahorrador | Administrador)", "activo (bool)") in app/models/usuario.py
- [X] T008 [P] Create Parametro versioned model ("clave", "valor", "vigente_desde", "vigente_hasta (null = actual)") with seed defaults (tasa mensual, tope 80%, monto mínimo, 5 días de gracia) in app/models/parametro.py
- [X] T009 Implement session auth helpers with bcrypt and deny-by-default role guard in app/deps.py (depends on T007)
- [X] T010 [P] Configure error handling and structured logging in app/main.py
- [X] T011 Implement automatic backup service (pg_dump diario retención 30 días en producción; copia versionada en SQLite/dev) in app/services/backups.py
- [X] T012 Create seed script for admin account and initial parameters in scripts/seed.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Acceso seguro por roles (Priority: P1)

**Goal**: Login con credenciales y acceso exclusivo por rol con error genérico (HU-05, FR-001)

**Independent Test**: Dos cuentas (ahorrador/admin) acceden a su panel; credenciales malas dan error genérico; ahorrador en ruta admin recibe 403 (QS-1)

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T013 [P] [US1] Acceptance test HU-05 login por roles y error genérico in tests/acceptance/test_hu05_auth.py
- [X] T014 [P] [US1] Integration test for cross-role denial (ahorrador → 403 en admin) in tests/integration/test_roles.py

### Implementation for User Story 1

- [X] T015 [US1] Implement login/logout routes (POST /login, POST /logout) with generic invalid-credentials error in app/routes/auth.py
- [X] T016 [P] [US1] Create login page template in app/templates/login.html
- [X] T017 [US1] Wire role guard into admin routes (deny-by-default) in app/routes/admin.py + app/main.py (guard in app/deps.py; depends on T009, T015)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Ahorradores, aportes y saldo (Priority: P1)

**Goal**: CRUD ahorradores, registro de aportes y consulta de saldo en tiempo real (HU-06, HU-01, HU-07; FR-002, FR-003, FR-004)

**Independent Test**: Registrar ahorrador (saldo cero) + 2 aportes → dashboard con saldo exacto e historial ordenado; fondo incluye ambos una vez (QS-2)

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T018 [P] [US2] Acceptance tests HU-06/HU-01/HU-07 (registro, aporte, saldo) in tests/acceptance/test_hu060107_aportes.py
- [X] T019 [P] [US2] Unit test for derived saldo (sum of aportes, no manual edits) in tests/unit/test_saldo.py

### Implementation for User Story 2

- [X] T020 [P] [US2] Create Ahorrador model ("documento (único)", "saldo inicial cero", "en_mora (derivado, no editable)") in app/models/ahorrador.py
- [X] T021 [P] [US2] Create append-only Aporte model ("fecha", "monto (> 0)", "comprobante (referencia de evidencia)") in app/models/aporte.py
- [X] T022 [US2] Implement ahorradores CRUD routes with unique-documento check and blocked baja ("baja bloqueada con saldo o préstamos activos") in app/routes/admin.py (depends on T020)
- [X] T023 [US2] Implement aporte registration route (fecha no futura, monto > 0, updates saldos once) in app/routes/admin.py (depends on T021)
- [X] T024 [P] [US2] Create ahorrador dashboard template (saldo, meta, movimientos propios, sin globales) in app/templates/dashboard.html
- [X] T025 [US2] Integrate dashboard with derived saldo and ordered history in app/routes/ahorrador.py (depends on T020, T021, T024)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Préstamos con cálculo de cuotas (Priority: P1)

**Goal**: Solicitud, aprobación/rechazo con tope y mora, y tabla de cuotas del motor único (HU-02, HU-03; FR-005, FR-006, FR-007)

**Independent Test**: Solicitud → Pendiente + aviso → aprobación genera cuotas; ancla $500k/12m ≈ $46.701; sobre tope y en mora bloqueados (QS-3)

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T026 [P] [US3] Acceptance tests HU-02/HU-03 (solicitud, aprobación/rechazo, topes, mora) in tests/acceptance/test_hu0203_prestamos.py
- [X] T027 [P] [US3] Unit test for finance engine anchor case
($500.000/12m → ~$46.701/mes, COP enteros, redondeo mitad arriba) in tests/unit/test_finance.py — kernel adelantado por Dev A para US7

### Implementation for User Story 3

- [X] T028 [P] [US3] Create Prestamo model with lifecycle ("estado (Pendiente → Aprobado/Rechazado → Activo → En mora → Pagado → Cerrado/Archivado)", "tasa_mensual_aplicada (snapshot)") in app/models/prestamo.py — kernel adelantado por Dev A para US7
- [X] T029 [P] [US3] Create Cuota model ("número", "valor", "fecha_vencimiento", "abonado (acumulado)", "estado (Pendiente | Parcial | Pagada | En mora)") in app/models/cuota.py — kernel adelantado por Dev A para US7 (agrega desglose capital/interés del motor)
- [X] T030 [US3] Implement single finance engine (amortización francesa sobre saldo pendiente, parámetros versionados) in app/services/finance.py (depends on T008, T028, T029) — kernel adelantado por Dev A para US7; Dev B lo usa en T032 sin duplicar
- [ ] T031 [US3] Implement solicitud route with tope validation ("min(% saldo, disponible)") and mora block in app/routes/ahorrador.py (depends on T030)
- [ ] T032 [US3] Implement atomic aprobar/rechazar routes with liquidity check and cuota generation in app/routes/admin.py (depends on T030)
- [ ] T033 [P] [US3] Create loan request template with live cuota estimate in app/templates/solicitud_prestamo.html

**Checkpoint**: All P1 stories (US1–US3) independently functional — núcleo del MVP

---

## Phase 6: User Story 4 - Pagos y mora automática (Priority: P2)

**Goal**: Abonos con recálculo y mora automática por días de gracia (HU-08; FR-008)

**Independent Test**: Abono total → Pagada; parcial → Parcial con remanente; vencida + 5 días → mora automática visible (QS-4)

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T034 [P] [US4] Acceptance test HU-08 (abono total/parcial, recálculo, estados) in tests/acceptance/test_hu08_pagos.py
- [ ] T035 [P] [US4] Unit test for automatic mora (grace days default 5, parametrizable) and RN-04 block lift on catch-up in tests/unit/test_mora.py

### Implementation for User Story 4

- [ ] T036 [US4] Implement mora evaluation service (scheduled + on-read, flag derivado) in app/services/mora.py
- [ ] T037 [US4] Implement pago registration route (valor > 0, fecha no futura, descuenta capital, recalcula) in app/routes/admin.py (depends on T036)
- [ ] T038 [US4] Create cartera view (activos, cuotas, mora automática) in app/templates/cartera.html (depends on T036)

**Checkpoint**: User Stories 1–4 work — operación completa del fondo (MVP funcional)

---

## Phase 7: User Story 5 - Reportes exportables (Priority: P2)

**Goal**: Consolidados filtrables con descarga Excel/PDF desde las consultas de vista (HU-09; FR-009)

**Independent Test**: Reportes por rango con totales correctos + descarga .xlsx y PDF; rango vacío → ceros (QS-5)

### Tests for User Story 5

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T039 [P] [US5] Acceptance test HU-09 (tipos, filtros, exportación, rango vacío) in tests/acceptance/test_hu09_reportes.py
- [ ] T040 [P] [US5] Integration test that report totals equal view queries (single source) in tests/integration/test_reportes.py

### Implementation for User Story 5

- [ ] T041 [US5] Implement report service (openpyxl + WeasyPrint: aportes, préstamos activos, mora, fondos) in app/services/reportes.py
- [ ] T042 [US5] Implement reportes routes with download responses in app/routes/admin.py (depends on T041)
- [ ] T043 [P] [US5] Create reportes page template with filters in app/templates/reportes.html

**Checkpoint**: User Stories 1–5 work — administración con visibilidad total

---

## Phase 8: User Story 6 - Notificaciones automáticas (Priority: P3)

**Goal**: Avisos de vencimiento, cambio de estado y recordatorios vía plataforma + correo (HU-10; FR-010)

**Independent Test**: Vencimiento y cambio de estado generan alerta con detalle; recordatorio en fecha (QS-6)

### Tests for User Story 6

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T044 [P] [US6] Acceptance test HU-10 (vencimiento, cambio de estado, recordatorio) in tests/acceptance/test_hu10_notificaciones.py

### Implementation for User Story 6

- [ ] T045 [P] [US6] Create Notificacion model ("tipo (vencimiento | cambio_estado | recordatorio_aporte)", "canal (plataforma | correo)") in app/models/notificacion.py
- [ ] T046 [US6] Implement notification service (in-app + SMTP configurable, plantillas) in app/services/notificaciones.py (depends on T045)
- [ ] T047 [US6] Hook notifications into prestamo state changes and vencimiento job in app/services/notificaciones.py (depends on T032, T036, T046)
- [ ] T048 [P] [US6] Create mis notificaciones template in app/templates/notificaciones.html

**Checkpoint**: User Stories 1–6 work — fondo con comunicación automática

---

## Phase 9: User Story 7 - Cierre y reparto anual (Priority: P3)

**Goal**: Liquidación de diciembre proporcional y auditable con cartera separada (HU-04; FR-011; RN-05)

**Independent Test**: Con datos conocidos, reparto por integrante cuadra con fondo; cartera activa separada (QS-7)

### Tests for User Story 7

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T049 [P] [US7] Acceptance test HU-04 (proporcionalidad, cuadre, detalle auditable) in tests/acceptance/test_hu04_reparto.py
- [X] T050 [P] [US7] Unit test for proportional reparto (mayor aporte → mayor utilidad; suma = fondo) in tests/unit/test_reparto.py

### Implementation for User Story 7

- [X] T051 [P] [US7] Create Reparto models (cierre + reparto_linea: "ahorro_aportado, utilidad_proporcional, total") in app/models/reparto.py
- [X] T052 [US7] Implement reparto service (corte diciembre, cartera como pendiente no disponible, marca Cerrados) in app/services/reparto.py (depends on T030, T051)
- [X] T053 [US7] Implement cierre route with per-member detail view in app/routes/admin.py (depends on T052)

**Checkpoint**: All user stories independently functional — ciclo anual completo

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T054 [P] Load test with 200+ ahorradores verifying < 3 s queries (SC-011) in tests/integration/test_carga.py
- [ ] T055 [P] Security hardening (login rate limit, 403 audit, session expiry) in app/deps.py and app/main.py
- [ ] T056 Run quickstart.md validation end-to-end (QS-1–QS-8) and fix gaps
- [ ] T057 [P] Documentation updates (README with setup, roles, parámetros) in README.md
- [ ] T058 Code cleanup and refactoring across app/ and tests/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3–9)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 10)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Integrates login (US1) but testable with seeded session
- **User Story 3 (P1)**: Depends on US2 entities (Ahorrador, saldos) - Needs T020/T021 patterns for tope validation
- **User Story 4 (P2)**: Depends on US3 (Préstamo, Cuota, finance engine)
- **User Story 5 (P2)**: Depends on US2–US4 data; implementation independent via shared queries
- **User Story 6 (P3)**: Hooks into US3 state changes (T032) and US4 mora (T036)
- **User Story 7 (P3)**: Depends on US2–US4 (aportes, préstamos, pagos)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T003/T004/T005 (Setup) can run in parallel - different files
- T007/T008 (Foundational models) can run in parallel - different files
- T010/T011 can run in parallel with T007–T009 - different files
- Once Foundational completes, US1 and US2 models/tests can start in parallel
- All acceptance/unit tests marked [P] run in parallel within each story
- T024/T033/T038/T043/T048 (templates) can run in parallel - different files

---

## Parallel Example: User Story 3

```bash
# Launch all tests for User Story 3 together:
Task: "Acceptance tests HU-02/HU-03 in tests/acceptance/test_hu0203_prestamos.py"
Task: "Unit test for finance engine anchor case in tests/unit/test_finance.py"

# Launch all models for User Story 3 together:
Task: "Create Prestamo model in app/models/prestamo.py"
Task: "Create Cuota model in app/models/cuota.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (auth)
4. Complete Phase 4: User Story 2 (ahorradores/aportes/saldo)
5. **STOP and VALIDATE**: Registrar ahorrador + aporte + consulta saldo end-to-end
6. Deploy/demo if ready

### Incremental Delivery (Release 1 → 3 del Story Mapping)

1. Setup + Foundational → Foundation ready
2. US1 + US2 → operación base (registro y ahorro)
3. US3 + US4 → ciclo de crédito completo = MVP funcional (Release 1)
4. US5 → administración informada (Release 2)
5. US6 + US7 → automatización y cierre (Release 2/3)
6. Phase 10 → carga, hardening, validación quickstart

### Parallel Team Strategy

Con tres desarrolladores (equipo de 3):

1. Los 3 juntos: Setup + Foundational (fases 1–2, checkpoint obligatorio).
2. Líneas de trabajo por dominio (cada dev es dueño de sus stories de punta a punta):
   - Dev A — línea base y cierre: US1 → US2 → US7 (auth, ahorradores/aportes/saldo, reparto anual).
   - Dev B — línea crédito: US3 → US4 (préstamos con motor financiero, pagos y mora automática).
   - Dev C — línea visibilidad: US5 → US6 (reportes exportables, notificaciones) y lidera Phase 10 (carga, quickstart, docs).
3. Puntos de sincronización (nadie avanza sin esto):
   - S1 tras Foundational: los 3 parten en paralelo (US1, tests+motor de US3, tests+modelos de US5 no se pisan: archivos distintos).
   - S2: B mergea T030–T032 (motor + aprobación) → desbloquea a C (T047 hooks) y a A para US7 (T052 usa el motor).
   - S3: B mergea T036 (mora) → C cierra T047; A puede validar US7 contra datos reales de US2–US4.
   - S4: los 3 en Phase 10 (C lidera carga/docs, A y B hardening de sus líneas + QS de sus stories).
4. Reglas: un story = un dueño; commits por tarea; PR por story con su test independiente en verde; si un bloqueo supera medio día, el bloqueado ayuda en la línea bloqueante en vez de abrir otro frente.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story independently completable and testable
- Verify tests fail before implementing (principio IV)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Restricciones de data-model citadas verbatim en cada tarea de modelo — no quedan a discreción de implementación
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
