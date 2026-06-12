"""
core/rate_limiter.py — Rate limiter en memoria para endpoints sensibles.
Thread-safe, offline-first, sin dependencias externas.
Claves: por usuario de sesión (primario) o por IP (fallback).
"""
import threading
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
from flask import jsonify, session, request

_log = logging.getLogger("sigca.rate_limiter")


class _BucketStore:
    """Almacén thread-safe de ventanas deslizantes por clave."""

    def __init__(self):
        self._lock = threading.Lock()
        self._store: dict[str, list] = defaultdict(list)

    def is_allowed(self, key: str, max_attempts: int, window_seconds: int) -> bool:
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)
        with self._lock:
            self._store[key] = [t for t in self._store[key] if t > cutoff]
            if len(self._store[key]) >= max_attempts:
                _log.warning("Rate limit alcanzado: key=%s intentos=%d", key, len(self._store[key]))
                return False
            self._store[key].append(now)
            return True

    def clear(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def purge_expired(self, window_seconds: int = 3600) -> None:
        """Limpia entradas vencidas para evitar crecimiento ilimitado."""
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        with self._lock:
            for key in list(self._store):
                self._store[key] = [t for t in self._store[key] if t > cutoff]
                if not self._store[key]:
                    del self._store[key]


_store = _BucketStore()


def _make_key(prefix: str) -> str:
    """Genera clave rate-limit: prefijo + usuario (o IP como fallback)."""
    usuario = session.get("nombre_usuario") or session.get("usuario_id")
    if usuario:
        return f"{prefix}:u:{usuario}"
    ip = request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr or "anon")
    return f"{prefix}:ip:{ip.split(',')[0].strip()}"


def limitar(prefix: str, max_attempts: int = 5, window_seconds: int = 60,
            mensaje: str = "Demasiados intentos. Espere unos minutos antes de reintentar."):
    """
    Decorador de rate limiting.
    Devuelve 429 JSON si se supera el límite.

    Ejemplo:
        @limitar("otp_enviar", max_attempts=3, window_seconds=60)
        @login_requerido
        def otp_enviar(): ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = _make_key(prefix)
            if not _store.is_allowed(key, max_attempts, window_seconds):
                return jsonify({"ok": False, "error": mensaje}), 429
            return f(*args, **kwargs)
        return wrapper
    return decorator
