"""core/backup_manager.py — Backups automaticos de la base de datos."""
import sqlite3, os, logging
from datetime import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

logger = logging.getLogger("sigca.backup")


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
    """
    Elimina backups por dos criterios (el más estricto gana):
    1. Índice >= BACKUPS_A_MANTENER (lista ordenada por mtime desc — más recientes primero)
    2. Más de 30 días de antigüedad
    """
    import time
    carpeta      = Config.BACKUP_FOLDER
    limite_tiempo = time.time() - (30 * 24 * 3600)
    archivos     = sorted(
        [f for f in os.listdir(carpeta) if f.startswith("paraguasmj_") and f.endswith(".db")],
        key=lambda n: os.path.getmtime(os.path.join(carpeta, n)),
        reverse=True,   # más reciente primero — los primeros N se preservan
    )
    for i, nombre in enumerate(archivos):
        ruta = os.path.join(carpeta, nombre)
        if i >= Config.BACKUPS_A_MANTENER or os.path.getmtime(ruta) < limite_tiempo:
            os.remove(ruta)
            logger.info(f"Backup eliminado: {nombre}")


def restaurar_backup(backup_path: str) -> dict:
    """
    Restaura la BD usando sqlite3.Connection.backup() — atómica y segura en modo WAL.
    Valida que la ruta esté dentro de BACKUP_FOLDER para prevenir path traversal.
    """
    import os
    ruta_backup = os.path.abspath(backup_path)
    backup_folder = os.path.abspath(Config.BACKUP_FOLDER)
    # Path traversal guard
    if not ruta_backup.startswith(backup_folder + os.sep) and ruta_backup != backup_folder:
        return {"success": False, "error": "Ruta de backup fuera del directorio permitido"}
    if not os.path.isfile(ruta_backup):
        return {"success": False, "error": f"Archivo no encontrado: {ruta_backup}"}
    try:
        # Verificar integridad del backup
        src = sqlite3.connect(ruta_backup)
        resultado = src.execute("PRAGMA integrity_check").fetchone()[0]
        if resultado != "ok":
            src.close()
            return {"success": False, "error": f"Integridad fallida: {resultado}"}
        # Restaurar atómicamente — sqlite3.backup() es seguro con WAL
        dst = sqlite3.connect(Config.DB_PATH)
        src.backup(dst)
        src.close()
        dst.close()
        logger.info(f"BD restaurada desde: {ruta_backup}")
        return {"success": True, "path": Config.DB_PATH, "restored_from": ruta_backup}
    except Exception as e:
        logger.error(f"Error restaurando backup: {e}")
        return {"success": False, "error": str(e)}
