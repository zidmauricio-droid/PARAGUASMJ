"""core/backup_manager.py — Backups automaticos de la base de datos."""
import sqlite3, os, logging
from datetime import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

logger = logging.getLogger("asuacap.backup")


def crear_backup() -> str:
    """
    Crea backup caliente con la API nativa de SQLite (segura en WAL mode).
    sqlite3.Connection.backup() es atómica incluso con escrituras concurrentes,
    a diferencia de shutil.copy2 que puede capturar WAL en estado inconsistente.
    """
    os.makedirs(Config.BACKUP_FOLDER, exist_ok=True)
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(Config.BACKUP_FOLDER, f"paraguasmj_{ts}.db")
    try:
        src = sqlite3.connect(Config.DB_PATH, timeout=30)
        dst = sqlite3.connect(destino)
        with src, dst:
            src.backup(dst, pages=500)   # 500 páginas por paso (~2MB) — no bloquea lectores
        src.close()
        dst.close()
        logger.info(f"Backup creado: {destino}")
        _limpiar_backups_antiguos()
        return destino
    except Exception as e:
        logger.error(f"Error en backup: {e}")
        return ""


def _limpiar_backups_antiguos():
    """Mantiene solo los N backups mas recientes."""
    archivos = sorted([
        f for f in os.listdir(Config.BACKUP_FOLDER)
        if f.startswith("paraguasmj_") and f.endswith(".db")
    ])
    while len(archivos) > Config.BACKUPS_A_MANTENER:
        a_borrar = os.path.join(Config.BACKUP_FOLDER, archivos.pop(0))
        os.remove(a_borrar)
        logger.info(f"Backup antiguo eliminado: {a_borrar}")
