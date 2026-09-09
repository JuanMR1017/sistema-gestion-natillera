# Research: Sistema de Gestión de Natillera

**Feature**: `specs/001-natillera-ahorros-prestamos/spec.md`
**Date**: 2026-09-09
**Status**: Todas las decisiones cerradas (0 NEEDS CLARIFICATION pendientes)

## R-01 — Stack backend + renderizado

- **Decision**: Python 3.13 con FastAPI, plantillas Jinja2 renderizadas en servidor,
  htmx para interacciones parciales y CSS propio responsive (identidad azul
  marino/blanco del prototipo Figma). Sin SPA ni cadena de build frontend.
- **Rationale**: El equipo trabaja en Python; FastAPI + TestClient hace triviales las
  pruebas de aceptación Gherkin (HU-01–HU-10); el server-render cubre las 3 vistas
  acordadas sin la complejidad de una SPA; cumple el principio V (simplicidad) y
  YAGNI de la constitución.
- **Alternatives considered**: Django (descartado: admin genérico y ORM monolítico
  sobran para roles custom y motor financiero propio); Flask (descartado: menos
  tipado/validación nativa que FastAPI); React/Vite SPA (descartada: build chain,
  doble validación cliente/servidor y más superficie de prueba para 3 vistas).

## R-02 — Base de datos y estrategia de respaldos

- **Decision**: PostgreSQL en producción y SQLite en desarrollo/pruebas, ambos tras
  patrón repositorio. Respaldos automáticos programados: `pg_dump` diario con
  retención de 30 días en producción; copia de archivo versionada en SQLite/dev.
- **Rationale**: RNF-08 exige backups automáticos y periódicos con historia real de
  recuperación; PostgreSQL tiene opciones gratuitas de hospedaje y file-lock sin
  riesgo en despliegue compartido; SQLite mantiene el desarrollo local y los tests
  rápidos y sin servicios externos. El repositorio evita fugas de SQL al dominio y
  permite la prueba de carga (SC-011, 200+ ahorradores) contra el motor real.
- **Alternatives considered**: Solo SQLite (descartado: riesgo de bloqueo de archivo
  en hosting compartido e historia de respaldo más débil); MySQL (descartado: sin
  ventaja frente a PostgreSQL para este dominio y menos familiaridad).

## R-03 — Autenticación y autorización

- **Decision**: Sesiones con cookie firmada, contraseñas con hash bcrypt, verificación
  de rol por ruta (deny-by-default) y error genérico ante credenciales inválidas.
  Visibilidad privada por defecto: el ahorrador solo ve su cuenta (clarificación
  sesión 2026-09-09); consolidados solo admin.
- **Rationale**: HU-05 y principio III lo exigen literalmente; las sesiones evitan
  gestionar tokens en un equipo que empieza; deny-by-default + minimización de datos
  satisfacen Ley 1581 sin debate adicional.
- **Alternatives considered**: JWT en localStorage (descartado: gestión de refresh y
  XSS innecesarios para app server-render); OAuth externo (descartado: fuera de
  alcance, sin proveedor definido por el grupo).

## R-04 — Motor financiero (cálculos)

- **Decision**: Módulo único `services/finance.py`: cuota por fórmula de amortización
  francesa sobre saldo de capital pendiente, tasa mensual y parámetros versionados
  (tasa, tope %, monto mínimo, días de gracia, redondeo COP sin decimales mitad hacia
  arriba). Recálculo total del saldo tras cada abono; estados de cuota
  Pendiente/Parcial/Pagada derivados, nunca editados.
- **Rationale**: Principio II (una sola ruta de cálculo auditable); el ejemplo de
  referencia $500.000/12m → ~$46.701/mes se convierte en test ancla; parámetros en
  tabla versionada cumplen RN-01/RN-02/RN-03 y FR-012.
- **Alternatives considered**: Cálculos repartidos en rutas/vistas (descartado: viola
  directamente el principio II); librería actuarial externa (descartada: dependencia
  innecesaria para amortización francesa estándar).

## R-05 — Mora automática y máquina de estados

- **Decision**: Evaluación de mora por trabajo programado + chequeo en cada lectura de
  cartera: cuota/aporte pasa a mora al superar los días de gracia (default 5,
  parametrizable); el bloqueo RN-04 se deriva del flag, sin acción manual.
  Préstamo: Pendiente → Aprobado/Rechazado → Activo → En mora → Pagado →
  Cerrado/Archivado (clarificaciones sesión 2026-09-09).
- **Rationale**: Respuestas A y C del clarify: automaticidad auditable + ciclo de vida
  explícito que el plan puede modelar y los tests recorrer de punta a punta.
- **Alternatives considered**: Mora manual por admin (descartada por el equipo en
  clarify); mora solo como flag sin estado de préstamo (descartada en clarify C).

## R-06 — Notificaciones

- **Decision**: Tabla de notificaciones en app (alerta en plataforma, canal base) +
  envío por SMTP configurable como canal complementario (plantillas: vencimiento,
  cambio de estado, recordatorio de aporte).
- **Rationale**: HU-10/FR-010 piden "correo o alerta"; la alerta interna funciona sin
  infraestructura externa (YAGNI) y el SMTP cubre el "omnicanal" del Release 3 sin
  atarse a un proveedor.
- **Alternatives considered**: Solo SMTP (descartado: exige servidor desde el día 1);
  WhatsApp/SMS vía proveedor (descartado: costo e integración fuera de alcance).

## R-07 — Reportes exportables

- **Decision**: Excel vía openpyxl y PDF vía WeasyPrint, generados desde las mismas
  consultas que las vistas (una sola fuente), con filtros por tipo y rango de fechas.
- **Rationale**: HU-09 exige PDF/Excel descargables; generar desde las consultas de
  vista garantiza que reporte y pantalla nunca diverjan (principio I).
- **Alternatives considered**: Solo CSV (descartado: el spec pide explícitamente
  PDF/Excel); servicio externo de reportes (descartado: YAGNI).

## R-08 — Pruebas

- **Decision**: pytest + TestClient de FastAPI + pytest-bdd (los Gherkin HU-01–HU-10
  como pruebas de aceptación), tests unitarios al motor financiero (incluido el caso
  ancla $500k/12m) y prueba de carga con 200+ ahorradores (SC-011).
- **Rationale**: Principio IV test-first; pytest-bdd convierte el Gherkin ya acordado
  con el curso en especificación ejecutable sin traducirlo a otro formato.
- **Alternatives considered**: behave (descartado: duplica runner fuera del stack
  pytest); tests solo manuales vía quickstart (descartado: no repetibles, violan IV).
