"""core/seguridad.py — Proteccion de rutas y sesiones."""
from functools import wraps
from flask import session, redirect, url_for, flash, request


def login_requerido(f):
    """Decorador: redirige al login si no hay sesion activa."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Debe iniciar sesion para acceder.", "warning")
            return redirect(url_for("autenticacion.login", next=request.path))
        return f(*args, **kwargs)
    return decorated


def rol_requerido(*roles):
    """Decorador: permite acceso solo a ciertos roles."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "usuario_id" not in session:
                return redirect(url_for("autenticacion.login"))
            if session.get("rol") not in roles:
                flash("No tiene permisos para realizar esta accion.", "danger")
                return redirect(url_for("dashboard.index"))
            return f(*args, **kwargs)
        return decorated
    return decorator
