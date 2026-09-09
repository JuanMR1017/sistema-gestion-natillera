# Data Model: Sistema de Gestión de Natillera

**Feature**: `specs/001-natillera-ahorros-prestamos/spec.md` · **Date**: 2026-09-09
Derivado del UML del Entregable #1 (Natillera, Administrador, Ahorrador, Aporte,
Préstamo, Cuota) más entidades exigidas por el spec (credenciales, parámetros,
notificaciones, reparto). Montos en COP enteros (sin decimales). Los saldos son
siempre derivados; movimientos append-only (sin UPDATE/DELETE de negocio).

## Usuario

Cuenta de acceso. Atributos: id, nombre de usuario (único), hash de contraseña
(bcrypt), rol (Ahorrador | Administrador), activo (bool), creado_en.
Relaciones: 1–1 con Ahorrador (si rol Ahorrador) o perfil Administrador.
Validación: FR-001; error genérico ante credenciales inválidas; deny-by-default.

## Ahorrador

Participante del fondo. Atributos: id, usuario_id (FK única), nombre, documento
(único), área, fecha_ingreso, en_mora (derivado, no editable).
Relaciones: 1 Usuario; N Aportes; N Préstamos (como solicitante).
Validación: FR-002 (saldo inicial cero; documento único; baja bloqueada con saldo
o préstamos activos); RN-04 (bloqueo de nuevas solicitudes en mora).

## Aporte

Movimiento de ahorro inmutable. Atributos: id, ahorrador_id (FK), fecha,
monto (> 0), comprobante (referencia de evidencia), registrado_por (admin),
registrado_en.
Efecto: incrementa saldo del ahorrador y fondo total (FR-003).
Validación: fecha no futura; monto > 0; ahorrador activo.

## Préstamo

Crédito interno. Atributos: id, solicitante_id (FK), monto, plazo_meses,
motivo, tasa_mensual_aplicada (snapshot del parámetro vigente), estado,
aprobado_por, fecha_solicitud, fecha_aprobación.
Estados: Pendiente → Aprobado/Rechazado → Activo → En mora → Pagado →
Cerrado/Archivado (clarify C). `En mora` se deriva de cuotas en mora; `Cerrado`
lo marca el reparto anual.
Validación: FR-005/FR-006 (tope = min(% saldo, disponible fondo); RN-02/RN-06);
transiciones solo hacia adelante, registradas con actor y fecha.

## Cuota

Obligación periódica inmutable salvo su estado derivado. Atributos: id,
prestamo_id (FK), número, valor, fecha_vencimiento, abonado (acumulado),
estado (Pendiente | Parcial | Pagada | En mora — mora automática tras días de
gracia, clarify A).
Efecto de abono (FR-008): incrementa `abonado`, recalcula saldo del préstamo,
actualiza estado; Parcial si abonado < valor, Pagada si igual.
Validación: generada solo por el motor (R-04); abono > 0 con fecha no futura.

## Parámetro

Configuración versionada del fondo. Atributos: id, clave (tasa_mensual,
tope_porcentaje_saldo, monto_minimo_aporte, dias_gracia_mora), valor,
vigente_desde, vigente_hasta (null = actual), modificado_por.
Validación: FR-012 (todo cambio versionado, nunca edición destructiva; los
préstamos conservan snapshot de la tasa aplicada).

## Notificación

Aviso automático. Atributos: id, destinatario_id (FK), tipo (vencimiento |
cambio_estado | recordatorio_aporte), detalle, canal (plataforma | correo),
leída, creada_en.
Validación: FR-010 (se genera ante el evento, no manualmente).

## Reparto (cierre anual)

Liquidación de diciembre. Atributos: id, ciclo_año, fecha_corte, fecha_ejecución,
ejecutado_por, total_fondo, total_utilidades.
Detalle por integrante: reparto_linea (reparto_id, ahorrador_id, ahorro_aportado,
utilidad_proporcional, total). Cartera activa al corte queda como pendiente,
no como disponible (Assumptions del spec).
Validación: FR-011 (suma de líneas = fondo; proporcional a aportes RN-05).

## Relaciones (resumen)

- Natillera 1 — 1..* Ahorrador (gestiona); Natillera 1 — 1..* Aporte vía ahorradores.
- Administrador 1 — 0..* Préstamo (aprueba); Administrador 1 — 0..* Aporte (registra).
- Ahorrador 1 — 0..* Aporte; Ahorrador 1 — 0..* Préstamo.
- Préstamo 1 — 1..* Cuota. Cuota N — 0..* abonos (registrados como movimientos de pago).
