"""
utils/audit.py
Registro de auditoría completo para PARAGUASMJ.
Fuente: PROGRAMA_3.doc — trazabilidad ante Contraloría, Auditoría SSPD.
Registra: quien, cuándo, qué, desde qué IP, con qué navegador.
"""
import json
import logging
from datetime import datetime
from functools import wraps
from flask import request, session
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("sigca.audit")


def log_action(usuario_id=None, nombre_usuario=None,
               accion: str = "ACTION", modulo: str = "sistema",
               descripcion: str = None, extra_data: dict = None) -> None:
    """
    Registra una acción en audit_log.
    Si no se pasan usuario_id/nombre, los obtiene de la sesión Flask activa.
    """
    from core.database_manager import get_db

    # Obtener datos de sesión si no se proveen
    if usuario_id is None:
        try:
            usuario_id = session.get("usuario_id")
        except RuntimeError:
            usuario_id = None
    if nombre_usuario is None:
        try:
            nombre_usuario = session.get("nombre_usuario", "sistema")
        except RuntimeError:
            nombre_usuario = "sistema"

    # IP y user-agent
    try:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "0.0.0.0"
        ua = request.headers.get("User-Agent", "")[:200]
    except RuntimeError:
        ip = "0.0.0.0"
        ua = ""

    # Serializar descripción
    desc = descripcion
    if extra_data:
        try:
            desc = json.dumps(extra_data, ensure_ascii=False)
        except Exception:
            desc = str(extra_data)

    try:
        conn = get_db()
        conn.execute("""
            INSERT INTO audit_log
            (usuario_id, nombre_usuario, accion, modulo, descripcion, ip_address, user_agent, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (usuario_id, nombre_usuario, accion, modulo, desc, ip, ua, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error guardando audit_log: {e}")


def audit(accion: str, modulo: str):
    """
    Decorador para auditar automáticamente una ruta Flask.
    Uso: @audit('CREATE', 'documentos')
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            result = f(*args, **kwargs)
            try:
                log_action(accion=accion, modulo=modulo,
                           descripcion=f"{request.method} {request.path}")
            except Exception:
                pass
            return result
        return decorated
    return decorator
