"""tests/test_otp.py — Pruebas del generador OTP."""
from core.otp_manager import generar_codigo_otp, CARACTERES_OTP

def test_longitud_otp():
    c = generar_codigo_otp(6)
    assert len(c) == 6

def test_caracteres_validos():
    for _ in range(100):
        c = generar_codigo_otp(6)
        for ch in c:
            assert ch in CARACTERES_OTP, f"Caracter invalido: {ch}"

def test_sin_ambiguedad():
    # Sin O, 0, I, 1
    for _ in range(100):
        c = generar_codigo_otp(8)
        for ch in ("O", "0", "I", "1"):
            assert ch not in c
