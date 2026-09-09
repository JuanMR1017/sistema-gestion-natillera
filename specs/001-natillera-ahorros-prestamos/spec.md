# Feature Specification: Sistema de Gestión de Natillera (Ahorros y Préstamos)

**Feature Branch**: `001-natillera-ahorros-prestamos`

**Created**: 2026-09-09

**Status**: Draft

**Input**: User description: "Sistema de información web que automatice la administración de la
natillera de ahorros y préstamos (Entregable #1 — ITM, Análisis y Diseño de Sistemas de
Información): centralizar ahorradores y aportes periódicos, automatizar solicitud/evaluación/
aprobación/seguimiento de préstamos internos, calcular automáticamente intereses, cuotas y
reparto proporcional de fin de año, y dar visibilidad en tiempo real de saldos, historiales y
estados de solicitud. Actores: Ahorrador, Administrador, Sistema. Alcance excluye pasarelas
de pago externas y declaraciones tributarias individuales."

## Clarifications

### Session 2026-09-09

- Q: ¿Cómo debe determinarse que un ahorrador está en mora y queda bloqueado para nuevos
  préstamos? → A: Automática por días (el sistema marca mora al superar los días de gracia
  parametrizados tras el vencimiento, por defecto 5 días; sin intervención manual).
- Q: ¿Qué estados debe tener un préstamo después de aprobado durante su vida hasta
  saldarse? → A: Ciclo completo (Pendiente → Aprobado/Rechazado → Activo → En mora →
  Pagado → Cerrado/Archivado tras el reparto anual).
- Q: ¿Cuántos ahorradores concurrentes debe soportar el sistema en el horizonte del
  proyecto? → A: Más de 200 (uso institucional amplio; exige diseño escalable y pruebas
  de carga).
- Q: ¿Qué información del fondo común puede ver un ahorrador más allá de su propia
  cuenta? → A: Solo la propia (saldo, historial y estados propios; los totales globales y
  el detalle por persona son exclusivos del Administrador).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Acceso seguro por roles (Priority: P1)

Ahorrador o Administrador inicia sesión con sus credenciales y accede únicamente a las
funciones de su rol; ante credenciales inválidas ve un error genérico sin revelación del
dato fallido (HU-05, RF-01).

**Why this priority**: Sin autenticación confiable no existe trazabilidad (no se sabe quién
registró qué) ni segregation por rol (RN-06). Es prerrequisito de todo el resto.

**Independent Test**: Se puede probar creando dos cuentas (ahorrador y administrador),
iniciando sesión con cada una y verificando paneles y bloqueo cruzado de funciones.

**Acceptance Scenarios**:

1. **Given** un usuario registrado con rol Ahorrador, **When** ingresa usuario y contraseña
   correctos y confirma, **Then** accede a su panel de ahorrador.
2. **Given** un usuario registrado con rol Administrador, **When** ingresa credenciales
   correctas, **Then** accede al panel de administración.
3. **Given** cualquier visitante, **When** ingresa credenciales inválidas, **Then** ve un
   mensaje de error genérico que no revela si falló el usuario o la contraseña.
4. **Given** un ahorrador autenticado, **When** intenta acceder a funciones exclusivas de
   administración (aprobar préstamos, generar reparto), **Then** el acceso es denegado.

---

### User Story 2 - Registrar ahorradores, aportes y consultar saldo (Priority: P1)

El Administrador registra empleados como ahorradores (nombre, documento, área, fecha de
ingreso, saldo inicial cero) y registra sus aportes periódicos (fecha, monto, comprobante);
el Ahorrador consulta en tiempo real su saldo acumulado, rendimiento proyectado e historial
ordenado por fecha (HU-06, HU-01, HU-07; RU-01, RU-02, RU-03; RF-02, RF-03, RF-04).

**Why this priority**: Es el corazón del MVP (Release 1): sin ahorradores ni aportes no hay
fondo ni operación. Elimina cuadernos y hojas de cálculo, causa raíz del problema.

**Independent Test**: Se puede probar registrando un ahorrador, cargándole dos aportes y
verificando como ahorrador que el saldo e historial reflejan exactamente lo registrado.

**Acceptance Scenarios**:

1. **Given** un administrador autenticado en el módulo de ahorradores, **When** ingresa
   nombre, documento, área y fecha de ingreso y confirma, **Then** se crea el perfil con
   saldo inicial en cero disponible para aportes.
2. **Given** un ahorrador activo seleccionado, **When** el administrador ingresa valor,
   fecha y confirma el aporte, **Then** el monto se suma al saldo del ahorrador, se
   actualiza el fondo total y se muestra confirmación.
3. **Given** un ahorrador autenticado en su panel, **When** abre "Mi saldo", **Then** ve
   saldo acumulado actual, rendimiento proyectado e historial completo ordenado por fecha.
4. **Given** un aporte ya confirmado, **When** se consulta el fondo total, **Then** incluye
   ese aporte exactamente una vez (sin duplicados ni omisiones).

---

### User Story 3 - Solicitar y aprobar préstamos con cálculo de cuotas (Priority: P1)

El Ahorrador solicita un préstamo (monto, plazo en meses, motivo); el sistema valida
elegibilidad (tope y mora) y lo deja en "Pendiente"; el Administrador lo aprueba o rechaza
verificando liquidez, y al aprobar se genera la tabla de cuotas con intereses según tasa
parametrizada (HU-02, HU-03; RU-04, RU-05, RU-07; RF-05, RF-06; RN-02, RN-03, RN-04, RN-06).

**Why this priority**: Completa el ciclo de valor del MVP: el ahorro existe para prestar.
Incluye las reglas de negocio más críticas (tope, mora, tasa).

**Independent Test**: Se puede probar con un ahorrador con saldo: solicitar, verificar estado
Pendiente y notificación al admin, aprobar como admin y verificar tabla de cuotas generada.

**Acceptance Scenarios**:

1. **Given** un ahorrador con saldo disponible y sin mora, **When** envía monto, plazo y
   motivo, **Then** la solicitud queda en "Pendiente" y se notifica al administrador.
2. **Given** una solicitud "Pendiente", **When** el administrador selecciona "Aprobar"
   con liquidez suficiente, **Then** el estado pasa a Aprobado y se genera la tabla de
   cuotas (amortización, cuota mensual, intereses por monto/plazo/tasa vigente).
3. **Given** una solicitud "Pendiente", **When** el administrador selecciona "Rechazar",
   **Then** el estado pasa a Rechazado y se notifica al ahorrador.
4. **Given** un ahorrador que pide más del tope (más del porcentaje parametrizado de su
   saldo o más del disponible del fondo), **When** envía la solicitud, **Then** el sistema
   la rechaza o impide el envío indicando el tope aplicable.
5. **Given** un ahorrador con cuotas o aportes en mora, **When** intenta solicitar un
   préstamo, **Then** la solicitud es bloqueada hasta ponerse al día.
6. **Given** un préstamo aprobado de $500.000 a 12 meses con la tasa vigente del ejemplo
   del prototipo, **When** se muestra el resumen, **Then** la cuota estimada es ~$46.701/mes
   con desglose de tasa visible.

---

### User Story 4 - Registrar pagos de cuotas y mantener cartera al día (Priority: P2)

El Administrador registra abonos a préstamos activos (valor, fecha); el sistema descuenta
capital, recalcula saldo pendiente y marca la cuota Pagada o Parcial (HU-08; RU-06; RF-07).

**Why this priority**: Release 1 (operación) y base del Release 2 (trazabilidad de cartera).
Sin pagos registrados el fondo se desfinancia y la mora es invisible.

**Independent Test**: Se puede probar con un préstamo aprobado con cuotas pendientes:
registrar un abono y verificar saldo recalculado y estado de cuota actualizado.

**Acceptance Scenarios**:

1. **Given** un préstamo activo con cuotas pendientes, **When** el administrador registra
   valor abonado y fecha y confirma, **Then** se descuenta el capital correspondiente, se
   recalcula el saldo pendiente y la cuota queda "Pagada" o "Parcial".
2. **Given** un abono parcial menor a la cuota, **When** se confirma, **Then** la cuota
   queda "Parcial" con el remanente visible y el saldo pendiente refleja solo lo abonado.
3. **Given** un ahorrador que estaba en mora y registra el pago que lo pone al día,
   **When** intenta solicitar un préstamo, **Then** el bloqueo por mora desaparece.
4. **Given** una cuota vencida que supera los días de gracia parametrizados sin pago,
   **When** el sistema evalúa la cartera, **Then** la cuota y el ahorrador quedan
   automáticamente en mora y visibles en el reporte de mora.

---

### User Story 5 - Reportes administrativos exportables (Priority: P2)

El Administrador genera reportes consolidados (aportes globales, préstamos activos,
indicadores de mora, fondos disponibles) por rango de fechas y los exporta en formato
descargable (HU-09; RU-10; RF-08).

**Why this priority**: Release 2: convierte datos trazables en decisiones (salud del fondo,
mora, liquidez). Sin reportes la administración sigue ciega aunque existan registros.

**Independent Test**: Se puede probar generando cada tipo de reporte con un rango de fechas
con datos conocidos y verificando totales y exportación descargable.

**Acceptance Scenarios**:

1. **Given** el administrador en el módulo de reportes, **When** elige tipo (aportes,
   préstamos activos o mora), rango de fechas y confirma, **Then** se consolida la
   información y se ofrece descarga (PDF/Excel).
2. **Given** un rango sin movimientos, **When** se genera el reporte, **Then** se muestra
   vacío con totales en cero en lugar de un error.
3. **Given** un reporte de mora, **When** existen cuotas vencidas impagas, **Then** cada
   una aparece con ahorrador, cuota, valor y días de mora.

---

### User Story 6 - Notificaciones automáticas (Priority: P3)

El Ahorrador recibe avisos automáticos ante vencimiento próximo de cuotas y cambios de
estado de sus solicitudes, por correo o alerta en plataforma (HU-10; RU-09; RF-09).

**Why this priority**: Release 2/3: reduce mora y carga administrativa recordando sin
consulta manual. Es mejora sobre un sistema ya operable.

**Independent Test**: Se puede probar provocando un vencimiento próximo y un cambio de
estado, y verificando que llega la notificación con el detalle correspondiente.

**Acceptance Scenarios**:

1. **Given** una cuota próxima a vencer de un ahorrador, **When** el sistema detecta el
   evento programado, **Then** envía notificación al ahorrador con el detalle (cuota,
   valor, fecha límite).
2. **Given** una solicitud del ahorrador que cambia de estado (aprobada/rechazada),
   **When** el administrador confirma el cambio, **Then** el ahorrador recibe notificación
   con el nuevo estado.
3. **Given** un recordatorio de aporte periódico configurado, **When** llega la fecha,
   **Then** el ahorrador recibe el recordatorio.

---

### User Story 7 - Cierre y reparto anual proporcional (Priority: P3)

El Administrador ejecuta en diciembre la liquidación: calcula utilidades por intereses y
consolida por integrante el total a entregar (ahorro + rendimiento proporcional a aportes)
(HU-04; RU-08; RF-10; RN-05).

**Why this priority**: Release 3: es el cierre del ciclo anual y la prueba de transparencia
final. Opera sobre un año de datos trazables; sin los stories previos no tiene sentido.

**Independent Test**: Se puede probar con un ciclo con aportes e intereses conocidos:
ejecutar el reparto y verificar que cada total = ahorro del integrante + utilidad
proporcional, y que la suma cuadra con el fondo.

**Acceptance Scenarios**:

1. **Given** alcanzada la fecha de corte del ciclo anual, **When** el administrador ejecuta
   el reparto anual, **Then** se calcula el rendimiento por intereses y se consolida por
   usuario el total a entregar proporcional a sus aportes.
2. **Given** dos integrantes con aportes distintos, **When** se ejecuta el reparto,
   **Then** quien aportó más recibe proporcionalmente más utilidad.
3. **Given** un reparto ya ejecutado, **When** se consulta el detalle, **Then** cada línea
   muestra ahorro aportado, utilidad asignada y total, y el consolidado cuadra con el fondo.

---

### Edge Cases

- ¿Qué ocurre cuando dos administradores intentan aprobar la misma solicitud "Pendiente"
  al mismo tiempo? Solo una aprobación MUST tener efecto; la otra MUST ver estado actualizado.
- ¿Cómo maneja el sistema un aporte con fecha futura o con monto cero/negativo? MUST
  rechazarlo con mensaje claro sin alterar saldos.
- ¿Qué ocurre cuando el fondo disponible es menor que el préstamo solicitado aunque el
  ahorrador esté dentro de su tope personal? La solicitud MUST bloquearse por liquidez
  insuficiente (aplica el menor de ambos topes, RN-02).
- ¿Cómo se comporta el reparto anual si hay préstamos activos no saldados al corte? El
  reparto MUST reflejar cartera pendiente separately y no repartir dinero prestado como si
  fuera disponible; el criterio exacto de neteo queda documentado en Assumptions.
- ¿Qué ocurre cuando se da de baja a un ahorrador con saldo o préstamos activos? La baja
  MUST bloquearse o exigir liquidación previa; nunca eliminar historial.
- ¿Cómo se garantiza que documento de ahorrador sea único? El registro con documento
  duplicado MUST rechazarse indicando el conflicto.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST autenticar usuarios con credenciales (usuario y contraseña),
  identificar su rol (Ahorrador o Administrador) y redirigir a su panel; ante credenciales
  inválidas MUST mostrar error genérico sin revelar el dato fallido.
- **FR-002**: El sistema MUST permitir al Administrador crear, consultar, actualizar y dar
  de baja ahorradores (nombre, documento único, área, fecha de ingreso) con saldo inicial
  en cero; la baja con saldo o préstamos activos MUST bloquearse o exigir liquidación previa.
- **FR-003**: El sistema MUST registrar aportes periódicos por ahorrador con fecha, monto
  mayor que cero y comprobante; cada aporte confirmado MUST sumar al saldo del ahorrador y
  al fondo total exactamente una vez.
- **FR-004**: El sistema MUST mostrar al Ahorrador su saldo acumulado, rendimiento
  proyectado e historial completo de movimientos ordenado por fecha, actualizado en tiempo
  real tras cada registro. El Ahorrador MUST NOT ver saldos, historiales ni totales
  globales de otros participantes; esa información consolidada es exclusiva del
  Administrador (Ley 1581, minimización de datos).
- **FR-005**: El sistema MUST registrar solicitudes de préstamo (monto, plazo en meses,
  motivo) en estado "Pendiente", validar tope (porcentaje parametrizado del saldo vs.
  disponible del fondo, aplica el menor) y bloqueo por mora, y notificar al Administrador.
  La mora se determina automáticamente: una cuota o aporte pasa a mora al superar los días
  de gracia parametrizados tras su vencimiento (por defecto 5 días), y el bloqueo de RN-04
  se levanta automáticamente al registrarse el pago que pone al día.
- **FR-006**: El sistema MUST permitir exclusivamente al Administrador aprobar o rechazar
  solicitudes "Pendiente" verificando liquidez; al aprobar MUST generar la tabla de cuotas
  (amortización, cuota mensual, intereses por monto/plazo/tasa vigente) y notificar al
  Ahorrador.
- **FR-007**: El sistema MUST calcular amortización, cuota mensual e intereses de cada
  préstamo con interés mensual parametrizado sobre saldo de capital pendiente, con fórmula
  y redondeo documentados y ejemplo de referencia ($500.000 / 12 meses → ~$46.701/mes).
- **FR-008**: El sistema MUST registrar cada abono a préstamo (valor, fecha), descontar
  capital, recalcular saldo pendiente y marcar la cuota "Pagada" o "Parcial" según
  corresponda.
- **FR-009**: El sistema MUST generar reportes exportables (PDF/Excel) de aportes globales,
  préstamos activos, indicadores de mora (ahorrador, cuota, valor, días) y fondos
  disponibles, filtrables por rango de fechas.
- **FR-010**: El sistema MUST emitir notificaciones automáticas (correo o alerta en
  plataforma) ante vencimiento próximo de cuotas, cambios de estado de solicitudes y
  recordatorios de aportes, con el detalle correspondiente.
- **FR-011**: El sistema MUST ejecutar el cierre y reparto anual a fecha de corte en
  diciembre, calculando utilidades por intereses y consolidando por integrante (ahorro +
  utilidad proporcional a aportes) con detalle auditable que cuadra con el fondo.
- **FR-012**: El sistema MUST parametrizar sin cambios de código: monto mínimo de ahorro
  periódico, porcentaje tope de préstamo sobre saldo, tasa de interés mensual y calendario
  de vencimientos/recordatorios; todo cambio de parámetro MUST quedar registrado con
  vigencia.
- **FR-013**: El sistema MUST proteger datos personales y financieros conforme a Ley 1581
  de 2012, cifrar credenciales, negar por defecto el acceso cruzado entre roles y mantener
  copias de seguridad automáticas y periódicas de la base de datos.
- **FR-014**: Fuera de alcance: integración con pasarelas de pago externas y generación de
  declaraciones tributarias individuales; el sistema MUST NOT prometerlas ni bloquearse por
  su ausencia.

### Key Entities

- **Ciclo de Natillera**: año operativo del fondo; atributos: año, fondo total derivado,
  tasa de interés vigente, monto mínimo de ahorro; contiene ahorradores, aportes,
  préstamos y un reparto anual.
- **Usuario (Ahorrador / Administrador)**: persona participante; ahorrador: nombre,
  documento único, área, fecha de ingreso, saldo derivado; administrador: facultades
  exclusivas de aprobación, registro de pagos y reparto.
- **Aporte**: movimiento de ahorro; atributos: ahorrador, fecha, monto, comprobante;
  incrementa saldo del ahorrador y fondo total.
- **Solicitud / Préstamo**: crédito interno; atributos: solicitante, monto, plazo en meses,
  motivo, tasa aplicada, estado (Pendiente → Aprobado/Rechazado → Activo → En mora →
  Pagado → Cerrado/Archivado tras el reparto anual); al aprobarse genera cuotas.
- **Cuota**: obligación periódica del préstamo; atributos: número, valor, fecha de
  vencimiento, estado (Pendiente/Parcial/Pagada/mora); recibe abonos que recalculan saldo.
- **Notificación**: aviso automático; atributos: destinatario, evento disparador
  (vencimiento, cambio de estado, recordatorio), detalle, canal (correo/alerta).
- **Reporte / Reparto anual**: consolidado administrativo filtrable por fechas y
  exportable; el reparto detalla por integrante ahorro, utilidad proporcional y total.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un administrador registra un ahorrador nuevo con datos básicos en menos de
  3 minutos sin ayuda externa.
- **SC-002**: Un aporte registrado se refleja en el saldo del ahorrador y en el fondo total
  de forma inmediata (consulta posterior muestra el nuevo valor sin intervención manual).
- **SC-003**: Las consultas de saldo y las solicitudes responden en menos de 3 segundos.
- **SC-004**: El sistema mantiene disponibilidad de al menos 95% durante las fechas
  operativas de aportes.
- **SC-005**: El 100% de los movimientos visibles (saldos, reportes, reparto) corresponde a
  registros trazables con actor, fecha, monto y evidencia; cero ajustes manuales fuera del
  sistema en una auditoría del ciclo.
- **SC-006**: El cálculo de referencia ($500.000 a 12 meses) produce la cuota esperada
  (~$46.701/mes) y el reparto de prueba cuadra al peso entre la suma por integrante y el
  fondo total.
- **SC-007**: Un ahorrador en mora no puede obtener un préstamo nuevo hasta ponerse al día
  (verificado en 100% de los intentos de prueba).
- **SC-008**: El 90% de los ahorradores completa sin ayuda su primera consulta de saldo y
  su primera solicitud de préstamo tras una demostración de 10 minutos.
- **SC-009**: Los reportes de aportes, préstamos activos y mora se generan y exportan
  (PDF/Excel) correctamente para cualquier rango de fechas con datos.
- **SC-010**: Toda aprobación/rechazo y todo vencimiento próximo genera su notificación
  al interesado con el detalle correspondiente.
- **SC-011**: El sistema soporta más de 200 ahorradores registrados con reportes y
  consultas dentro de los mismos umbrales de tiempo (verificado con prueba de carga).

## Assumptions

- Ciclo anual calendario con corte de reparto en diciembre; el grupo define al inicio el
  monto mínimo de ahorro y la tasa mensual, ambos parametrizables (RN-01, RN-03).
- Tope de préstamo por defecto: 80% del saldo del ahorrador o disponible del fondo, el
  menor (RN-02); ajustable por el grupo sin cambiar código.
- Interés mensual sobre saldo de capital pendiente; moneda COP sin decimales; redondeo
  mitad hacia arriba documentado en el plan.
- Préstamos activos al corte de diciembre se reflejan como cartera pendiente en el reparto
  y no como disponible; el detalle de neteo se fija en el plan y se valida con el equipo
  docente antes de implementar.
- Notificaciones por alerta en plataforma como canal base y correo como canal
  complementario configurable; sin pasarelas de pago externas en esta fase.
- Navegadores objetivo Chrome, Edge, Firefox y dispositivos móviles; usuarios con
  conectividad estándar; administración centralizada en rol Administrador.
- Escala objetivo: más de 200 ahorradores registrados (uso institucional amplio); el plan
  MUST incluir diseño escalable y prueba de carga que verifique SC-011.
- Entidades y Gherkin del Entregable #1 (HU-01–HU-10, RF-01–RF-10, RN-01–RN-07) son la
  fuente de verdad funcional; el diagrama UML (Natillera, Administrador, Ahorrador,
  Aporte, Préstamo, Cuota) y el prototipo Figma (3 vistas azul marino/blanco) guían el
  plan sin agregar alcance.
