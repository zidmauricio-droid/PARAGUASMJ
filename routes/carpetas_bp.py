"""
routes/carpetas_bp.py — Blueprint para gestión de carpetas documentales
"""
from flask import Blueprint, render_template, request, jsonify, session, abort
from utils.file_manager import file_manager
from utils.seguridad import login_required, admin_required, auditor_required, generar_token_csrf, verificar_token_csrf
from utils.auditoria import auditoria_manager

carpetas_bp = Blueprint("carpetas", __name__, url_prefix="/carpetas")


@carpetas_bp.route("/")
@login_required
def index():
    stats = file_manager.obtener_estadisticas()
    modulos = file_manager.obtener_modulos()
    csrf = generar_token_csrf()
    return render_template("carpetas/index.html",
                           stats=stats, modulos=modulos, csrf_token=csrf)


@carpetas_bp.route("/crear_estructura", methods=["POST"])
@login_required
def crear_estructura_completa():
    if session.get("rol") != "admin":
        return jsonify({"ok": False, "error": "Solo administradores"}), 403
    if not verificar_token_csrf():
        return jsonify({"ok": False, "error": "Token CSRF inválido"}), 400

    ok, msg, creadas = file_manager.crear_estructura_completa()
    auditoria_manager.registrar(
        accion="CREAR_ESTRUCTURA_COMPLETA",
        usuario=session.get("usuario_nombre", "desconocido"),
        detalle=f"{len(creadas)} carpetas creadas",
        nivel="INFO",
        ip=request.remote_addr or ""
    )
    return jsonify({"ok": ok, "mensaje": msg, "creadas": creadas})


@carpetas_bp.route("/crear", methods=["POST"])
@login_required
def crear_carpeta():
    if not verificar_token_csrf():
        return jsonify({"ok": False, "error": "Token CSRF inválido"}), 400
    data = request.get_json(force=True, silent=True) or {}
    modulo = data.get("modulo", "").strip()
    nombre = data.get("nombre", "").strip()
    if not modulo or not nombre:
        return jsonify({"ok": False, "error": "Módulo y nombre requeridos"}), 400

    ok, msg = file_manager.crear_carpeta_personalizada(modulo, nombre)
    if ok:
        auditoria_manager.registrar(
            accion="CREAR_CARPETA",
            usuario=session.get("usuario_nombre", "desconocido"),
            detalle=f"{modulo}/{nombre}",
            nivel="INFO",
            ip=request.remote_addr or ""
        )
    return jsonify({"ok": ok, "mensaje": msg})


@carpetas_bp.route("/eliminar", methods=["POST"])
@login_required
def eliminar():
    if session.get("rol") != "admin":
        return jsonify({"ok": False, "error": "Solo administradores"}), 403
    if not verificar_token_csrf():
        return jsonify({"ok": False, "error": "Token CSRF inválido"}), 400
    data = request.get_json(force=True, silent=True) or {}
    modulo = data.get("modulo", "").strip()
    nombre = data.get("nombre", "").strip()
    if not modulo or not nombre:
        return jsonify({"ok": False, "error": "Módulo y nombre requeridos"}), 400

    ok, msg = file_manager.eliminar_carpeta(modulo, nombre)
    if ok:
        auditoria_manager.registrar(
            accion="ELIMINAR_CARPETA",
            usuario=session.get("usuario_nombre", "desconocido"),
            detalle=f"{modulo}/{nombre}",
            nivel="WARNING",
            ip=request.remote_addr or ""
        )
    return jsonify({"ok": ok, "mensaje": msg})


@carpetas_bp.route("/explorar/<modulo>")
@login_required
def explorar_modulo(modulo):
    sub = request.args.get("sub", "")
    resultado = file_manager.explorar_carpeta(modulo, sub)
    return jsonify(resultado)


@carpetas_bp.route("/estadisticas")
@login_required
def estadisticas():
    return jsonify(file_manager.obtener_estadisticas())


@carpetas_bp.route("/auditoria")
@login_required
def auditoria():
    if session.get("rol") not in ("admin", "auditor"):
        abort(403)
    n = min(int(request.args.get("n", 100)), 500)
    entradas = auditoria_manager.obtener_ultimos(n)
    return jsonify({"ok": True, "entradas": entradas, "total": len(entradas)})


@carpetas_bp.route("/modulos")
@login_required
def listar_modulos():
    return jsonify({"modulos": file_manager.obtener_modulos()})


@carpetas_bp.route("/verificar_integridad")
@login_required
def verificar_integridad():
    if session.get("rol") not in ("admin", "auditor"):
        abort(403)
    resultado = auditoria_manager.verificar_integridad()
    return jsonify(resultado)
