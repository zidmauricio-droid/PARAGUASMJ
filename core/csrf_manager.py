"""
core/csrf_manager.py — Autoridad única de CSRF para todo PARAGUASMJ.
Todo el sistema debe consumir exclusivamente desde aquí.
Clave de sesión: 'csrf_token' (compatible con utils/seguridad.py y core/secure_auth.py).
"""
import secrets
import hmac
from flask import session, request


_SESSION_KEY = "csrf_token"


def generar_token() -> str:
    """Genera (o reutiliza) el token CSRF de la sesión activa."""
    if _SESSION_KEY not in session:
        session[_SESSION_KEY] = secrets.token_hex(32)
    return session[_SESSION_KEY]


def verificar_token() -> bool:
    """
    Verifica el token CSRF. Lee automáticamente de:
    1. request.form['csrf_token']
    2. Header X-CSRF-Token
    3. JSON body csrf_token
    """
    token_enviado = (
        request.form.get(_SESSION_KEY)
        or request.headers.get("X-CSRF-Token")
        or (request.get_json(silent=True) or {}).get(_SESSION_KEY)
    )
    token_sesion = session.get(_SESSION_KEY)
    if not token_enviado or not token_sesion:
        return False
    return hmac.compare_digest(
        token_enviado.encode() if isinstance(token_enviado, str) else token_enviado,
        token_sesion.encode()  if isinstance(token_sesion, str)  else token_sesion,
    )


def csrf_requerido(f):
    """Decorador: rechaza métodos mutantes sin CSRF válido."""
    from functools import wraps
    from flask import jsonify, abort
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            if not verificar_token():
                if request.accept_mimetypes.best == "application/json" or \
                   request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify({"error": "Token CSRF inválido"}), 403
                abort(403)
        return f(*args, **kwargs)
    return wrapper
