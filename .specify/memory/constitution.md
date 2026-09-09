<!--
Sync Impact Report:
- Version change: 0.0.0 (plantilla sin ratificar) → 1.0.0
- Modified principles: ninguno previo; se crean I–V desde cero a partir del Entregable #1
  (RU-01–RU-10, RF-01–RF-10, RNF-01–RNF-09, RN-01–RN-07, HU-01–HU-10).
- Added sections: "Restricciones Técnicas y Cumplimiento" (stack, alcance, RNF, RN);
  "Flujo de Desarrollo y Gates de Calidad" (Releases 1–3 del User Story Mapping, gates Gherkin).
- Removed sections: ninguna; se reemplazaron todos los placeholders de la plantilla.
- Follow-up TODOs: ninguno. Sin tokens pendientes.
-->

# Sistema de Gestión de Natillera Constitution

## Core Principles

### I. Trazabilidad financiera total (NON-NEGOTIABLE)

Todo movimiento del fondo MUST quedar registrado como entidad inmutable con
actor, fecha, monto y evidencia: aportes (fecha, monto, comprobante),
solicitudes y cambios de estado de préstamos (Pendiente/Aprobado/Rechazado),
abonos de cuotas (valor, fecha, capital descontado, saldo recalculado) y
reparto anual (corte diciembre, total por integrante). Los saldos MUST ser
siempre valores derivados de movimientos registrados, nunca editados a mano.
Ningún flujo operativo fuera del sistema (cuadernos, hojas de cálculo,
mensajería) es válido como fuente de verdad.

Rationale: el problema raíz es la administración manual sin trazabilidad
(errores de cálculo, demoras, desconfianza). Sin este principio el sistema
reproduce el problema que pretende resolver.

### II. Cálculos deterministas, parametrizados y auditables

Intereses, amortización, cuotas y reparto proporcional MUST calcularse en una
única ruta de código con parámetros explícitos y versionados: tasa de interés
mensual sobre saldo de capital pendiente (RN-03), monto mínimo de ahorro
periódico (RN-01), tope de préstamo = min(80% del saldo del ahorrador,
disponible del fondo común) salvo parametrización del grupo (RN-02), y
reparto en diciembre proporcional a aportes más utilidades (RN-05). El
redondeo (COP sin decimales) y la fórmula de cuota MUST estar documentados y
cubiertos por pruebas con los ejemplos del prototipo (ej. $500.000 a 12 meses
→ ~$46.701/mes). Todo recalculo tras un abono MUST actualizar saldo
pendiente y estado de cuota (Pagada/Parcial).

Rationale: los cálculos manuales son la principal fuente de error; un solo
motor auditable elimina divergencias entre vistas, reportes y cierre anual.

### III. Seguridad por roles y protección de datos (NON-NEGOTIABLE)

El sistema MUST autenticar con usuario y contraseña con hash robusto,
identificar el rol (Ahorrador / Administrador) y redirigir al panel
correspondiente; ante credenciales inválidas MUST mostrar un error genérico
sin revelar qué dato falló (HU-05). La aprobación o rechazo de créditos es
exclusiva del Administrador (RN-06). Un ahorrador en mora de aportes o cuotas
MUST NOT poder solicitar nuevos préstamos hasta ponerse al día (RN-04). Los
retiros anticipados solo proceden por excepción validada por administración
(RN-07). El tratamiento de datos personales y financieros MUST cumplir la Ley
1581 de 2012 (Habeas Data, Colombia) y la base de datos MUST contar con
backups automáticos y periódicos (RNF-08).

Rationale: es dinero común entre empleados; una falla de autorización o
fuga de datos destruye la confianza y tiene implicación legal.

### IV. Test-First con Gherkin como contrato de aceptación (NON-NEGOTIABLE)

Cada historia HU-01–HU-10 del Entregable #1 MUST existir como prueba de
aceptación Dado/Cuando/Entonces antes de implementar: registrar aporte,
solicitar préstamo, aprobar/rechazar, reparto anual, autenticación,
registrar ahorrador, consultar saldo, registrar pago de cuota, reportes
(PDF/Excel), notificaciones automáticas. Flujo Red-Green-Refactor
estrictamente enforced: pruebas escritas → falla verificada → implementación
→ verde. Las reglas RN-01–RN-07 MUST tener casos de borde (tope superado,
mora bloqueante, reparto proporcional, retiro anticipado denegado).

Rationale: el dominio financiero no admite "casi funciona"; el Gherkin ya
acordado con el curso es la especificación ejecutable.

### V. Simplicidad operativa, usabilidad responsive y rendimiento

La interfaz MUST ser web responsive (Chrome, Edge, Firefox + móvil),
intuitiva con curva mínima de aprendizaje, con la identidad FinTech
acordada (azul marino/blanco) y las tres vistas estratégicas: Dashboard del
Ahorrador (saldo, meta del ciclo, movimientos), Solicitar Préstamo
(formulario con cálculo estimado de cuota) y Panel de Administración
(métricas del fondo, prestado/disponible, tarjetas aprobar/rechazar).
Consultas de saldo y solicitudes MUST responder en < 3 s (RNF-04) y el
sistema MUST mantener disponibilidad ≥ 95% en fechas operativas de aportes
(RNF-03). La arquitectura MUST ser modular para soportar crecimiento de
ahorradores sin degradar rendimiento (RNF-05, RNF-07). YAGNI: fuera de
alcance pasarelas de pago externas y declaraciones tributarias.

Rationale: los usuarios son empleados no técnicos que hoy operan por
mensajería; si el sistema no es más simple y rápido que el cuaderno, no se
adopta.

## Restricciones Técnicas y Cumplimiento

Stack objetivo: aplicación web con backend modular y base de datos
relacional con backups automáticos. Sin decisión de framework aún — se
define en `/speckit.plan` y NO se asume aquí.

Alcance incluido (RU/RF): autenticación por roles (RF-01), CRUD de
ahorradores con saldo inicial cero (RF-02, HU-06), registro de aportes con
fecha/monto/comprobante (RF-03, HU-01), estado de cuenta con saldo,
rendimiento proyectado e historial (RF-04, HU-07), gestión de solicitudes
con estados (RF-05, HU-02, HU-03), cálculo automático de cuotas (RF-06),
registro de pagos con recálculo (RF-07, HU-08), reportes exportables de
aportes/préstamos/mora/fondos (RF-08, HU-09), notificaciones automáticas de
vencimientos y cambios de estado (RF-09, HU-10), cierre y reparto anual
proporcional a corte diciembre (RF-10, HU-04).

Alcance excluido: integración con pasarelas de pago externas y generación
de declaraciones tributarias individuales (fase posterior).

Cumplimiento obligatorio: ISO/IEC 25010 (seguridad, usabilidad,
fiabilidad/disponibilidad y recuperabilidad, eficiencia de desempeño,
compatibilidad, mantenibilidad, portabilidad/adaptabilidad) y Ley 1581 de
2012 para datos personales y financieros (RNF-01–RNF-09).

## Flujo de Desarrollo y Gates de Calidad

Backbone (actividades clave): Gestionar Ahorradores, Registrar Aportes,
Gestionar Préstamos, Registrar Pagos de Cuotas, Reportes y Cierre Anual.

Entregas por Releases del Story Mapping: Release 1 / MVP (registrar
ahorrador, aporte periódico, solicitar/aprobar préstamo, pago de cuota,
consulta de saldo); Release 2 / Automatización e Historial (edición y baja,
historial, cálculo automático de intereses, alertas de vencimiento,
reportes de cartera); Release 3 / Alertas Avanzadas y Cierre (notificación
de estado de solicitud, alerta de mora, reparto anual automatizado).

Gates obligatorios antes de dar por hecho cada incremento: (1) pruebas
Gherkin en verde para las HU del incremento; (2) verificación cruzada de
consistencia especificación → plan → tareas; (3) revisión de trazabilidad
(todo monto visible en UI existe como movimiento registrado); (4)
verificación de roles (ahorrador no accede a funciones de admin y viceversa).
Los artefactos viven en `specs/` y evolucionan solo cuando cambia el
comportamiento intencionado, no con cada refactor interno.

## Governance

Esta constitución es la máxima autoridad de gobierno del proyecto y
prevalece sobre cualquier práctica, plantilla o decisión ad hoc. Toda
funcionalidad MUST demostrar conformidad con los principios I–V y con las
reglas RN-01–RN-07 en su especificación, plan, tareas e implementación.

Procedimiento de enmienda: cualquier cambio a principios, restricciones o
gates MUST documentarse con justificación, impacto en `specs/` y plan de
migración; cambios menores los aprueba el equipo (Santiago Suárez Osorio /
Juan Carlos Monsalve Restrepo), cambios mayores (redefinición o eliminación
de un principio NON-NEGOTIABLE) requieren aprobación explícita del equipo
docente. Versionado semántico: MAJOR por eliminaciones o redefiniciones
incompatibles de gobierno, MINOR por principios o secciones nuevas o guía
materialmente ampliada, PATCH por clarificaciones y redacción.

Revisiones de cumplimiento: cada PR y cada comando `/speckit.*` MUST
verificar adherencia a esta constitución; la complejidad adicional MUST
justificarse por escrito; lo no regulado aquí se rige por las guías de
runtime del proyecto una vez existan.

**Version**: 1.0.0 | **Ratified**: 2026-09-09 | **Last Amended**: 2026-09-09
