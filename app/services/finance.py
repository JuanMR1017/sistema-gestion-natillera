"""Motor financiero único: amortización, imputación y reparto (principio II).

Toda cifra monetaria en COP enteros (redondeo mitad hacia arriba). Dev B extiende
este módulo con la generación de tabla al aprobar (T032); la matemática vive aquí.
"""

from __future__ import annotations

import calendar
from datetime import date


def redondear(pesos: float) -> int:
    return int(pesos + 0.5)


def cuota_francesa(monto: int, tasa: float, plazo: int) -> int:
    if plazo <= 0:
        raise ValueError("El plazo debe ser mayor que cero.")
    if tasa <= 0:
        return redondear(monto / plazo)
    return redondear(monto * tasa / (1 - (1 + tasa) ** -plazo))


def sumar_meses(fecha: date, n: int) -> date:
    m = fecha.month - 1 + n
    ano, mes = fecha.year + m // 12, m % 12 + 1
    return date(ano, mes, min(fecha.day, calendar.monthrange(ano, mes)[1]))


def tabla_cuotas(monto: int, tasa: float, plazo: int, primera_fecha: date) -> list[dict]:
    """Cronograma francés; la última cuota absorbe el residuo para cuadrar capital."""
    valor = cuota_francesa(monto, tasa, plazo)
    filas, saldo = [], monto
    for n in range(1, plazo + 1):
        interes = redondear(saldo * tasa)
        capital = valor - interes
        if n == plazo:
            capital, valor = saldo, saldo + interes
        # La primera cuota vence un mes después de la aprobación.
        filas.append({
            "numero": n, "valor": valor, "capital": capital, "interes": interes,
            "fecha_vencimiento": sumar_meses(primera_fecha, n),
        })
        saldo -= capital
    return filas


def imputar_pago(valor: int, capital: int, interes: int, abonado: int, monto: int):
    """Imputa un abono: primero a interés, luego a capital. Retorna
    (a_interes, a_capital, nuevo_abonado, estado)."""
    if monto <= 0:
        raise ValueError("El abono debe ser mayor que cero.")
    nuevo = abonado + monto
    a_interes = min(nuevo, interes) - min(abonado, interes)
    a_capital = monto - a_interes
    estado = "Pagada" if nuevo >= valor else ("Parcial" if nuevo > 0 else "Pendiente")
    return a_interes, a_capital, nuevo, estado


def interes_cobrado(valor: int, interes: int, abonado: int) -> int:
    """Porción de interés ya cobrada de una cuota (interés primero)."""
    _ = valor
    return min(max(abonado, 0), interes)


def reparto_proporcional(aportes: dict[int, int], total_utilidades: int) -> dict[int, int]:
    """Reparte utilidades proporcional a aportes; resto por mayor fracción (cuadra exacto)."""
    total = sum(aportes.values())
    if total <= 0 or total_utilidades <= 0:
        return {k: 0 for k in aportes}
    base = {k: (v * total_utilidades) // total for k, v in aportes.items()}
    resto = total_utilidades - sum(base.values())
    fraccion = sorted(aportes, key=lambda k: (aportes[k] * total_utilidades) % total,
                      reverse=True)
    for k in fraccion[:resto]:
        base[k] += 1
    return base
