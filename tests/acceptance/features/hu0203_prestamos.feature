# language: es
Característica: Solicitud y aprobación de préstamos (HU-02, HU-03)

  Escenario: Solicitar préstamo
    Dado un ahorrador con saldo disponible y sin mora
    Cuando solicita un préstamo de 200000 a 6 meses por "Mejora de vivienda"
    Entonces la solicitud queda en "Pendiente" y se avisa al administrador

  Escenario: Aprobar préstamo genera tabla de cuotas
    Dado una solicitud "Pendiente" con liquidez suficiente
    Cuando el administrador la aprueba
    Entonces el préstamo genera su tabla de cuotas con intereses

  Escenario: Rechazar préstamo
    Dado una solicitud "Pendiente" de un ahorrador
    Cuando el administrador la rechaza por "Liquidez comprometida"
    Entonces la solicitud queda en "Rechazado" y se avisa al ahorrador

  Escenario: Cuota de referencia del prototipo
    Dado la tasa mensual vigente es 1.8%
    Cuando se estima un préstamo de 500000 a 12 meses
    Entonces la cuota estimada es 46701 con desglose de tasa visible

  Escenario: Tope de préstamo
    Dado un ahorrador con saldo 100000
    Cuando solicita un préstamo de 90000 a 6 meses por "Prueba de tope"
    Entonces la solicitud es bloqueada indicando el tope aplicable

  Escenario: Mora bloquea solicitud
    Dado un ahorrador con una cuota en mora
    Cuando solicita un préstamo de 50000 a 6 meses por "Prueba de mora"
    Entonces la solicitud es bloqueada hasta ponerse al día
