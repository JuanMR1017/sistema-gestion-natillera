"""Unitarias del reparto proporcional: exactitud al peso (T050)."""

from app.services.finance import reparto_proporcional


def test_mayor_aporte_mayor_utilidad_y_suma_exacta():
    out = reparto_proporcional({1: 800000, 2: 200000}, 10000)
    assert out[1] == 8000
    assert out[2] == 2000
    assert sum(out.values()) == 10000


def test_resto_por_mayor_fraccion_sin_perder_pesos():
    out = reparto_proporcional({1: 1, 2: 1, 3: 1}, 100)
    assert sum(out.values()) == 100
    assert sorted(out.values()) == [33, 33, 34]


def test_sin_aportes_o_sin_utilidad_reparte_cero():
    assert reparto_proporcional({}, 5000) == {}
    assert reparto_proporcional({1: 1000}, 0) == {1: 0}
