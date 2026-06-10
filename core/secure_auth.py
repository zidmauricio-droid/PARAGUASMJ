"""
PARAGUASMJ - Autenticacion y CSRF seguros.
Firma correcta de auditar(), verify_csrf_token() sin argumentos.
"""
import secrets
from datetime import datetime
from functools import wraps
from flask import session, request, jsonify, current_app


# ── CSRF ─────────────────────────────────────────────────────────────────────

_CSRF_KEY = "csrf_token"   # unificado con utils/seguridad.py


def generate_csrf_token() -> str:
    """Genera (o reutiliza) un token CSRF en la sesion actual."""
    if _CSRF_KEY not in session:
        session[_CSRF_KEY] = secrets.token_hex(32)
    return session[_CSRF_KEY]


def verify_csrf_token() -> bool:
    """
    Verifica el token CSRF. SIN ARGUMENTOS — lee de request automaticamente.
    Busca en: request.form → X-CSRF-Token header → request.json.
    """
    token: str | None = (
        request.form.get("csrf_token")
        or request.headers.get("X-CSRF-Token")
        or (request.get_json(silent=True) or {}).get("csrf_token")
    )
    stored = session.get(_CSRF_KEY)
    if not token or not stored:
        return False
    return secrets.compare_digest(token, stored)


def csrf_protect(f):
    """Decorador que protege rutas mutantes con verificacion CSRF."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            if not verify_csrf_token():
                return jsonify({"error": "CSRF token invalido"}), 403
        return f(*args, **kwargs)
    return wrapper


# ── AUDITORIA ────────────────────────────────────────────────────────────────

def auditar(accion: str, detalle: str = "", modulo: str = "general") -> bool:
    """
    Registra evento de auditoria.

    Firma: auditar(accion, detalle="", modulo="general")
    NO pasar usuario= — se extrae de session internamente.
    """
    from core.database_manager import get_db
    try:
        usuario = session.get("nombre_usuario", "anonimo")
        ip      = getattr(request, "remote_addr", "0.0.0.0") or "0.0.0.0"
        conn    = get_db()
        conn.execute(
            """INSERT INTO logs_sistema (nivel, modulo, usuario, accion, detalle, ip_origen)
               VALUES ('AUDIT', ?, ?, ?, ?, ?)""",
            (modulo, usuario, accion, detalle, ip),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        try:
            current_app.logger.error("auditar() error: %s", exc)
        except RuntimeError:
            pass
        return False
