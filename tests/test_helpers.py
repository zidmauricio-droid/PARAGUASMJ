"""tests/test_helpers.py — Pruebas de helpers."""
from utils.helpers import formatear_moneda, calcular_ianc, truncar

def test_moneda_cero():
    assert "0" in formatear_moneda(0)

def test_moneda_positivo():
    r = formatear_moneda(1500000)
    assert "1.500.000" in r

def test_truncar_corto():
    assert truncar("Hola", 60) == "Hola"

def test_truncar_largo():
    t = truncar("A"*100, 60)
    assert t.endswith("...")
    assert len(t) <= 63
