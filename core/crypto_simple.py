"""
core/crypto_simple.py
Cifrado simétrico ligero sin dependencias externas.
Usa XOR con keystream SHA-256 derivado de SECRET_KEY.
Propósito: proteger contraseñas en BD SQLite de lectura directa.
No apto para datos altamente sensibles expuestos en red.
"""
import hashlib
import base64
import os

_PREFIX = "enc1:"


def _derive_key(salt: bytes) -> bytes:
    from config import Config
    material = Config.SECRET_KEY.encode() + salt
    return hashlib.sha256(material).digest()


def _xor_stream(data: bytes, key_seed: bytes) -> bytes:
    stream = b""
    block = key_seed
    while len(stream) < len(data):
        block = hashlib.sha256(block).digest()
        stream += block
    return bytes(a ^ b for a, b in zip(data, stream))


def cifrar(texto: str) -> str:
    """Cifra texto plano; retorna cadena con prefijo enc1: almacenable en BD."""
    if not texto:
        return texto
    if texto.startswith(_PREFIX):
        return texto
    salt = os.urandom(16)
    key  = _derive_key(salt)
    ct   = _xor_stream(texto.encode(), key)
    return _PREFIX + base64.b64encode(salt + ct).decode()


def descifrar(valor: str) -> str:
    """Descifra valor cifrado con cifrar(). Si no tiene prefijo, lo devuelve tal cual."""
    if not valor or not valor.startswith(_PREFIX):
        return valor
    raw  = base64.b64decode(valor[len(_PREFIX):])
    salt = raw[:16]
    ct   = raw[16:]
    key  = _derive_key(salt)
    return _xor_stream(ct, key).decode()
