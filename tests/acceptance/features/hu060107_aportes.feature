# language: es
Característica: Ahorradores, aportes y saldo (HU-06, HU-01, HU-07)

  Escenario: Registrar ahorrador
    Dado un administrador autenticado en el módulo de ahorradores
    Cuando registra nombre "Ana Ruiz", documento "123", área "Ventas" y fecha de ingreso "2026-01-15"
    Entonces el ahorrador queda creado con saldo inicial en cero y disponible para aportes

  Escenario: Registrar aporte
    Dado un ahorrador activo con documento "123"
    Cuando el administrador registra un aporte de 125000 con fecha "2026-02-01"
    Entonces el saldo del ahorrador aumenta en 125000 y el fondo total se actualiza

  Escenario: Consultar saldo
    Dado un ahorrador autenticado con 2 aportes de 125000
    Cuando abre "Mi saldo"
    Entonces ve saldo acumulado 250000, rendimiento proyectado y el historial ordenado por fecha

  Escenario: Documento duplicado
    Dado un ahorrador con documento "123"
    Cuando el administrador registra otro ahorrador con documento "123"
    Entonces el registro es rechazado sin crear duplicados
