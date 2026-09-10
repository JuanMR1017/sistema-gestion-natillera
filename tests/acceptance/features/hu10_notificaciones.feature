# language: es
Característica: Notificaciones automáticas (HU-10)

  Escenario: Aviso por cambio de estado
    Dado una solicitud de préstamo de un ahorrador
    Cuando el administrador la aprueba
    Entonces el ahorrador recibe el aviso con el nuevo estado

  Escenario: Alerta de vencimiento próximo
    Dado un préstamo con una cuota que vence en 2 días
    Cuando el ahorrador abre sus avisos
    Entonces ve la alerta con cuota, valor y fecha límite

  Escenario: Recordatorio de aporte periódico
    Dado un ahorrador sin aportes en los últimos 40 días
    Cuando el ahorrador abre sus avisos
    Entonces recibe el recordatorio con el monto mínimo vigente
