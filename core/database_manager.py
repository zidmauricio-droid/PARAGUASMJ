"""
core/database_manager.py — Conexiones SQLite centralizadas.
"""
import sqlite3, logging, os, sys
from contextlib import contextmanager
from typing import Any, Dict, List, Tuple
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

logger = logging.getLogger("asuacap.db")

# Whitelist completa de tablas operativas del proyecto
TABLAS_PERMITIDAS = frozenset({
    "documentos", "versiones_documento", "firmantes_documento",
    "control_consecutivos", "logs_sistema", "usuarios", "pqrs",
    "fallas_gis", "puntos_gis", "balance_hidrico", "proyectos",
    "finanzas_movimientos", "convenios", "emergencias", "suscriptores",
})


def get_db() -> sqlite3.Connection:
    """Retorna conexion SQLite con row_factory y PRAGMAs de rendimiento activos."""
    conn = sqlite3.connect(Config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA cache_size = -20000")
    return conn


@contextmanager
def db_connection(autocommit: bool = True):
    """
    Context manager para conexiones seguras con commit/rollback automático.

    autocommit=True (default): commit al salir sin excepción, rollback ante error.
    autocommit=False: el caller gestiona commit; rollback automático ante error.
    """
    conn = get_db()
    try:
        yield conn
        if autocommit:
            conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_consecutivo(area: str, tipo: str, anio: int) -> int:
    """Obtiene el siguiente consecutivo. Operación atómica con UPDATE+RETURNING."""
    with db_connection() as conn:
        cur = conn.execute("""
            UPDATE control_consecutivos SET ultimo = ultimo + 1
            WHERE area=? AND tipo_documento=? AND anio=?
            RETURNING ultimo
        """, (area, tipo, anio))
        r = cur.fetchone()
        if r:
            return r[0]
        conn.execute("""
            INSERT INTO control_consecutivos(area, tipo_documento, anio, ultimo)
            VALUES (?, ?, ?, 1)
        """, (area, tipo, anio))
        return 1


def registrar_log(nivel: str, modulo: str, usuario: str, accion: str,
                  detalle: str = "", ip: str = "") -> None:
    """Registra en logs_sistema. Firma compatible con todos los call sites existentes."""
    try:
        with db_connection() as conn:
            conn.execute("""
                INSERT INTO logs_sistema(nivel, modulo, usuario, accion, detalle, ip_origen)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nivel, modulo, usuario, accion, detalle, ip))
    except Exception as e:
        logger.error(f"Error log: {e}")


def ejecutar_transaccion(queries: List[Tuple[str, tuple]]) -> bool:
    """Ejecuta múltiples queries en una sola transacción atómica."""
    with db_connection() as conn:
        for sql, params in queries:
            conn.execute(sql, params)
    return True


def verificar_conexion() -> bool:
    """Verifica que la base de datos sea accesible."""
    try:
        with db_connection(autocommit=False) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def obtener_estadisticas_bd() -> Dict:
    """Estadísticas de la base de datos para panel de administración."""
    ruta = Config.DB_PATH
    size = os.path.getsize(ruta) if os.path.isfile(ruta) else 0
    with db_connection(autocommit=False) as conn:
        tablas = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        indices = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index'"
        ).fetchone()[0]
        journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
    return {
        "path":       ruta,
        "size_bytes": size,
        "size_mb":    round(size / (1024 * 1024), 2),
        "tables":     tablas,
        "indexes":    indices,
        "journal_mode": journal,
    }
