"""
core/crypto_simple.py
ADVERTENCIA INSTITUCIONAL: Este módulo provee OFUSCACIÓN OPERATIVA, NO cifrado institucional fuerte.
- Usa XOR con keystream SHA-256 derivado de SECRET_KEY.
- Un atacante con acceso al código fuente Y a la BD puede recuperar los secretos.
- Propósito exclusivo: proteger contraseñas SMTP/API en BD SQLite contra lectura directa.
- NO usar para datos sensibles expuestos en red, credenciales bancarias o información personal.
- Para cifrado institucional fuerte usar cryptography.Fernet o AES-GCM.
- AUDIT: cada uso queda registrado en audit_log con CONFIG_ENCRYPTION_WEAK.
"""
import hashlib
import base64
import logging
import os

logger = logging.getLogger("sigca.crypto")

_PREFIX = "enc1:"


def es_cifrado_institucional() -> bool:
    """Siempre retorna False. Ninguna entidad debe asumir que este módulo provee cifrado normativo."""
    return False


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


def _audit_weak(operacion: str) -> None:
    """Registra en audit_log que se usó cifrado débil (ofuscación)."""
    try:
        from utils.audit import log_action
        log_action(
            accion="CONFIG_ENCRYPTION_WEAK",
            modulo="crypto_simple",
            descripcion=f"Uso de ofuscación XOR-SHA256 ({operacion}) — NO es cifrado institucional fuerte"
        )
    except Exception:
        logger.warning(f"CONFIG_ENCRYPTION_WEAK: {operacion} — ofuscación operativa usada")


def cifrar(texto: str) -> str:
    """Ofusca texto plano; retorna cadena con prefijo enc1: almacenable en BD.
    PRECAUCIÓN: es_cifrado_institucional() == False. Solo protege contra lectura directa en SQLite."""
    if not texto:
        return texto
    if texto.startswith(_PREFIX):
        return texto
    _audit_weak("cifrar")
    salt = os.urandom(16)
    key  = _derive_key(salt)
    ct   = _xor_stream(texto.encode(), key)
    return _PREFIX + base64.b64encode(salt + ct).decode()


def descifrar(valor: str) -> str:
    """Revierte ofuscación de cifrar(). Si no tiene prefijo, devuelve tal cual."""
    if not valor or not valor.startswith(_PREFIX):
        return valor
    raw  = base64.b64decode(valor[len(_PREFIX):])
    salt = raw[:16]
    ct   = raw[16:]
    key  = _derive_key(salt)
    return _xor_stream(ct, key).decode()
