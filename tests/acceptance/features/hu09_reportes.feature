# language: es
Característica: Reportes administrativos exportables (HU-09)

  Escenario: Reporte de aportes con descarga
    Dado movimientos registrados en el rango 2026-01-01 a 2026-12-31
    Cuando el administrador genera el reporte de aportes del rango
    Entonces ve los totales correctos y puede descargar Excel y PDF

  Escenario: Rango vacío sin error
    Dado movimientos registrados en el rango 2026-01-01 a 2026-12-31
    Cuando el administrador genera el reporte de aportes de 2025-01-01 a 2025-01-31
    Entonces ve la tabla vacía con totales en cero

  Escenario: Reporte de mora con detalle
    Dado una cuota vencida impaga de un ahorrador
    Cuando el administrador genera el reporte de mora
    Entonces cada cuota aparece con ahorrador, valor y días de mora
