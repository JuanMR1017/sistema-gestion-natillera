# language: es
Característica: Pagos de cuotas y mora automática (HU-08)

  Escenario: Abono total de cuota
    Dado un préstamo activo con cuotas pendientes
    Cuando el administrador registra el abono total de la primera cuota
    Entonces la cuota queda "Pagada" y el saldo pendiente se recalcula

  Escenario: Abono parcial de cuota
    Dado un préstamo activo con cuotas pendientes
    Cuando el administrador registra un abono parcial de la primera cuota
    Entonces la cuota queda "Parcial" con el remanente visible

  Escenario: Pago pone al día y desbloquea
    Dado un ahorrador en mora por una cuota vencida
    Cuando registra el pago que lo pone al día
    Entonces puede solicitar un préstamo nuevo

  Escenario: Mora automática por días de gracia
    Dado un préstamo con una cuota vencida hace 10 días sin pago
    Cuando se evalúa la cartera
    Entonces la cuota y el ahorrador quedan en mora y visibles en cartera
