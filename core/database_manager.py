"""
core/database_manager.py — Conexiones SQLite centralizadas.
"""
import sqlite3, logging, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

logger = logging.getLogger("asuacap.db")


def get_db() -> sqlite3.Connection:
    """Retorna conexion SQLite con row_factory y foreign_keys activos."""
    conn = sqlite3.connect(Config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def obtener_consecutivo(area: str, tipo: str, anio: int) -> int:
    """Obtiene el siguiente consecutivo. Operacion atomica."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE control_consecutivos SET ultimo = ultimo + 1
            WHERE area=? AND tipo_documento=? AND anio=?
            RETURNING ultimo
        """, (area, tipo, anio))
        r = cur.fetchone()
        if not r:
            cur.execute("""
                INSERT INTO control_consecutivos(area,tipo_documento,anio,ultimo)
                VALUES(?,?,?,1)
            """, (area, tipo, anio))
            n = 1
        else:
            n = r[0]
        conn.commit()
        return n
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Error consecutivo {area}-{tipo}-{anio}: {e}")
        raise
    finally:
        conn.close()


def registrar_log(nivel, modulo, usuario, accion, detalle="", ip=""):
    """Registra en logs_sistema."""
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO logs_sistema(nivel,modulo,usuario,accion,detalle,ip_origen)
            VALUES(?,?,?,?,?,?)
        """, (nivel, modulo, usuario, accion, detalle, ip))
        conn.commit()
    except Exception as e:
        logger.error(f"Error log: {e}")
    finally:
        conn.close()
