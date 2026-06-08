"""
utils/seguridad.py — Decoradores de sesión, CSRF, y bloqueo por intentos fallidos
"""
import os, hashlib, time, logging
from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify, abort, g

logger = logging.getLogger("asuacap.seguridad")

SESSION_TIMEOUT    = 30 * 60   # 30 minutos
MAX_INTENTOS       = 5
BLOQUEO_SEGUNDOS   = 15 * 60   # 15 minutos

_intentos: dict = {}   # {ip: {"count": n, "desde": t}}


def _es_ajax() -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest" or \
           request.accept_mimetypes.best == "application/json"


def login_required(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        if "usuario_id" not in session:
            if _es_ajax():
                return jsonify({"error": "sesion_expirada"}), 401
            flash("Debe iniciar sesión", "warning")
            return redirect(url_for("auth.login"))
        ultimo = session.get("ultimo_acceso", 0)
        if time.time() - ultimo > SESSION_TIMEOUT:
            session.clear()
            if _es_ajax():
                return jsonify({"error": "sesion_expirada"}), 401
            flash("Sesión expirada por inactividad", "warning")
            return redirect(url_for("auth.login"))
        session["ultimo_acceso"] = time.time()
        return f(*args, **kwargs)
    return decorado


def admin_required(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Debe iniciar sesión", "warning")
            return redirect(url_for("auth.login"))
        if session.get("rol") != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorado


def auditor_required(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Debe iniciar sesión", "warning")
            return redirect(url_for("auth.login"))
        if session.get("rol") not in ("admin", "auditor"):
            abort(403)
        return f(*args, **kwargs)
    return decorado


def verificar_permiso(permiso: str):
    def decorator(f):
        @wraps(f)
        def decorado(*args, **kwargs):
            if "usuario_id" not in session:
                abort(401)
            permisos = session.get("permisos", [])
            if permiso not in permisos and session.get("rol") != "admin":
                abort(403)
            return f(*args, **kwargs)
        return decorado
    return decorator


def generar_token_csrf() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = hashlib.sha256(os.urandom(32)).hexdigest()
    return session["csrf_token"]


def verificar_token_csrf() -> bool:
    token_form    = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    token_session = session.get("csrf_token")
    if not token_form or not token_session:
        return False
    return hmac_compare(token_form, token_session)


def hmac_compare(a: str, b: str) -> bool:
    import hmac as _hmac
    return _hmac.compare_digest(a.encode() if isinstance(a, str) else a,
                                 b.encode() if isinstance(b, str) else b)


def registrar_intento_fallo(ip: str):
    entrada = _intentos.setdefault(ip, {"count": 0, "desde": time.time()})
    if time.time() - entrada["desde"] > BLOQUEO_SEGUNDOS:
        entrada["count"] = 0
        entrada["desde"] = time.time()
    entrada["count"] += 1
    logger.warning(f"Intento fallido #{entrada['count']} desde {ip}")


def esta_bloqueado(ip: str) -> bool:
    entrada = _intentos.get(ip)
    if not entrada:
        return False
    if time.time() - entrada["desde"] > BLOQUEO_SEGUNDOS:
        del _intentos[ip]
        return False
    return entrada["count"] >= MAX_INTENTOS


def limpiar_intentos(ip: str):
    _intentos.pop(ip, None)
