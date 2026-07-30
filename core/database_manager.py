"""
core/database_manager.py — Conexiones SQLite centralizadas.
"""
import sqlite3, logging, os, sys
from contextlib import contextmanager
from typing import Any, Dict, List, Tuple
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

logger = logging.getLogger("sigca.db")

# Whitelist completa de tablas operativas del proyecto
TABLAS_PERMITIDAS = frozenset({
    "documentos", "versiones_documento", "firmantes_documento",
    "control_consecutivos", "logs_sistema", "usuarios", "pqrs",
    "fallas_gis", "puntos_gis", "balance_hidrico", "proyectos",
    "finanzas_movimientos", "convenios", "emergencias", "suscriptores",
    # Tablas financieras — agregadas RC5.5
    "caja_chica", "bancos", "movimientos_financieros",
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


def limpiar_borradores_antiguos(dias: int = 30) -> int:
    """Elimina documentos en estado Borrador con más de `dias` días de antigüedad."""
    with db_connection() as conn:
        cur = conn.execute("""
            DELETE FROM registro_central
            WHERE estado = 'Borrador'
            AND julianday('now') - julianday(fecha_creacion) > ?
        """, (dias,))
        return cur.rowcount


def limpiar_por_tabla(tabla: str, campo_pk: str, valor: Any) -> int:
    """
    Elimina registros por PK con validación de whitelist.
    Solo opera sobre tablas declaradas en TABLAS_PERMITIDAS.
    """
    if tabla not in TABLAS_PERMITIDAS:
        raise ValueError(f"Tabla '{tabla}' no permitida para borrado")
    with db_connection() as conn:
        cur = conn.execute(f"DELETE FROM {tabla} WHERE {campo_pk} = ?", (valor,))
        return cur.rowcount


def obtener_tablas() -> List[str]:
    """Lista las tablas del esquema actual. Útil para diagnóstico."""
    with db_connection(autocommit=False) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [r["name"] for r in rows]


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


# ── Alias RC5.5 — compatibilidad con call sites existentes ──────────
# atomic  = db_connection con autocommit=True  (escritura transaccional)
# readonly = db_connection con autocommit=False (solo lectura, sin commit)
atomic   = db_connection            # atomic(autocommit=True) es el default


def readonly():
    """Context manager de solo lectura — no emite COMMIT al salir."""
    return db_connection(autocommit=False)


def validar_columnas(tabla: str, columnas: list) -> list:
    """
    Filtra columnas contra el esquema real de la tabla.
    Previene inyeccion via nombres de columna dinamicos.
    Retorna solo las columnas que existen en la tabla.
    """
    with db_connection(autocommit=False) as conn:
        info = conn.execute(f"PRAGMA table_info({tabla})").fetchall()
        cols_validas = {r["name"] for r in info}
    return [c for c in columnas if c in cols_validas]
