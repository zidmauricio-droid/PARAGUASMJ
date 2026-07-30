"""
core/metrics.py — Métricas de rendimiento RC5.5.x
Decorator @medir_tiempo para endpoints lentos. Sin dependencias externas.
Umbrales: warning >1s, crítico >5s. Registra en audit_log con acción SLOW_ENDPOINT.
"""
import time
import logging
import functools
from typing import Callable

logger = logging.getLogger("sigca.metrics")

_UMBRAL_WARNING_S  = 1.0
_UMBRAL_CRITICO_S  = 5.0


def medir_tiempo(nombre_endpoint: str):
    """
    Decorator que mide el tiempo de ejecución de una función y registra
    advertencia si supera 1 segundo, crítico si supera 5 segundos.

    Uso:
        @docs_bp.route("/documentos")
        @medir_tiempo("documentos_listar")
        def listar():
            ...
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            try:
                return f(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - t0
                if elapsed >= _UMBRAL_CRITICO_S:
                    logger.warning(
                        "SLOW_ENDPOINT CRITICO: %s tardó %.2fs (umbral %.1fs)",
                        nombre_endpoint, elapsed, _UMBRAL_CRITICO_S
                    )
                    _registrar_metrica(nombre_endpoint, elapsed, "CRITICO")
                elif elapsed >= _UMBRAL_WARNING_S:
                    logger.info(
                        "SLOW_ENDPOINT WARNING: %s tardó %.2fs",
                        nombre_endpoint, elapsed
                    )
                    _registrar_metrica(nombre_endpoint, elapsed, "WARNING")
        return wrapper
    return decorator


def _registrar_metrica(endpoint: str, elapsed_s: float, nivel: str) -> None:
    """Registra en audit_log si está disponible. No lanza excepción si falla."""
    try:
        from utils.audit import log_action
        log_action(
            accion="SLOW_ENDPOINT",
            modulo="metrics",
            descripcion=f"{nivel}: {endpoint} tardó {elapsed_s:.2f}s"
        )
    except Exception:
        pass


def obtener_stats_cache_clasificador() -> dict:
    """Retorna estadísticas de la caché LRU del clasificador archivístico."""
    try:
        from core.document_classifier import _determinar_serie_cached
        info = _determinar_serie_cached.cache_info()
        return {
            "hits":      info.hits,
            "misses":    info.misses,
            "maxsize":   info.maxsize,
            "currsize":  info.currsize,
            "hit_ratio": round(info.hits / max(info.hits + info.misses, 1) * 100, 1),
        }
    except Exception:
        return {"error": "cache_info no disponible"}
