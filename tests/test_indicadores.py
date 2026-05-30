"""tests/test_indicadores.py — Pruebas de indicadores CRA."""
import pytest
from core.indicadores import calcular_ianc

def test_ianc_normal():
    assert calcular_ianc(1000, 800) == 20.0

def test_ianc_cero_produccion():
    assert calcular_ianc(0, 100) is None

def test_ianc_sin_perdidas():
    assert calcular_ianc(1000, 1000) == 0.0

def test_ianc_alta():
    assert calcular_ianc(1000, 300) == 70.0
