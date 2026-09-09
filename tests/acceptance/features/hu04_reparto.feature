# language: es
Característica: Cierre y reparto anual (HU-04)

  Escenario: Reparto proporcional auditable
    Dado un ciclo con aportes de 250000 y una cuota con 10000 de interés cobrado
    Cuando el administrador ejecuta el reparto del año 2026 con corte "2026-12-31"
    Entonces cada integrante recibe su ahorro más la utilidad proporcional y el total cuadra con el fondo

  Escenario: Reparto ya ejecutado
    Dado un reparto ejecutado para el año 2026
    Cuando el administrador lo ejecuta de nuevo
    Entonces es rechazado sin duplicar el reparto
