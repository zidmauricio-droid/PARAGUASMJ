"""
PARAGUASMJ - Autenticacion y CSRF seguros.
Firma correcta de auditar(), verify_csrf_token() sin argumentos.
"""
import secrets
from datetime import datetime
from functools import wraps
from flask import session, request, jsonify, current_app


# ── CSRF ─────────────────────────────────────────────────────────────────────

# ── CSRF — delega a core/csrf_manager (autoridad única) ─────────────
def generate_csrf_token() -> str:
    from core.csrf_manager import generar_token
    return generar_token()


def verify_csrf_token() -> bool:
    from core.csrf_manager import verificar_token
    return verificar_token()


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
