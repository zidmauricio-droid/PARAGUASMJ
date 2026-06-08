"""core/auditoria.py — Registro de acciones para auditoria SSPD."""
from flask import session, request
from core.database_manager import registrar_log


def auditar(accion: str, detalle: str = "", modulo: str = "general"):
    """Registra una accion de auditoria en logs_sistema."""
    usuario = session.get("nombre_usuario", "anonimo")
    ip = request.remote_addr or ""
    registrar_log("AUDIT", modulo, usuario, accion, detalle, ip)


# Alias de compatibilidad para call sites que usan registrar_evento
def registrar_evento(accion: str, detalle: str = "", modulo: str = "general"):
    """Alias de auditar() — compatibilidad con call sites existentes."""
    auditar(accion, detalle, modulo)
