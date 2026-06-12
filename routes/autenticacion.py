"""routes/autenticacion.py — Login, logout, perfil y logo institucional."""
import time
import base64
from flask import (Blueprint, render_template, request, session,
                   redirect, url_for, flash, jsonify)
from werkzeug.security import check_password_hash, generate_password_hash
from core.database_manager import get_db, registrar_log
from core.seguridad import login_requerido, rol_requerido
from utils.seguridad import esta_bloqueado, registrar_intento_fallo, limpiar_intentos
from datetime import datetime

auth_bp = Blueprint("autenticacion", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_id" in session:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        ip      = request.remote_addr or "0.0.0.0"
        if esta_bloqueado(ip):
            flash("Acceso bloqueado temporalmente por múltiples intentos fallidos. Intente en 15 minutos.", "danger")
            return render_template("login.html")
        usuario = request.form.get("usuario", "").strip()
        clave   = request.form.get("clave", "")
        conn    = get_db()
        u = conn.execute(
            "SELECT * FROM usuarios WHERE nombre_usuario=? AND activo=1",
            (usuario,)
        ).fetchone()
        conn.close()
        if u and check_password_hash(u["password_hash"], clave):
            limpiar_intentos(ip)
            session["usuario_id"]     = u["pk_usuario_id"]
            session["nombre_usuario"] = u["nombre_usuario"]
            session["nombre_completo"]= u["nombre_completo"]
            session["rol"]            = u["rol"]
            session["ultimo_acceso"]  = time.time()
            registrar_log("INFO","auth",usuario,"login","","")
            return redirect(url_for("dashboard.index"))
        registrar_intento_fallo(ip)
        flash("Usuario o contraseña incorrectos", "danger")
    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    nombre = session.get("nombre_usuario","")
    registrar_log("INFO","auth",nombre,"logout","","")
    session.clear()
    return redirect(url_for("autenticacion.login"))


@auth_bp.route("/perfil")
@login_requerido
def perfil():
    return render_template("perfil.html")


# ── Logo institucional ──────────────────────────────────────────────

@auth_bp.route("/logo/cargar", methods=["POST"])
@login_requerido
@rol_requerido("admin")
def cargar_logo():
    """Carga el logo institucional. Solo administrador."""
    from core.logo_manager import guardar_logo
    from config import Config
    archivo = request.files.get("logo")
    if not archivo or not archivo.filename:
        return jsonify({"ok": False, "error": "Seleccione un archivo"}), 400
    resultado = guardar_logo(archivo.read(), archivo.filename, Config.DB_PATH)
    if resultado.get("ok"):
        from utils.audit import log_action
        log_action(accion="UPLOAD_LOGO", modulo="configuracion",
                   descripcion=f"Logo actualizado: {archivo.filename}")
    return jsonify(resultado)


@auth_bp.route("/logo/actual")
@login_requerido
def logo_actual():
    """Retorna datos del logo actual para todo el sistema."""
    from core.logo_manager import obtener_logo
    from config import Config
    info = obtener_logo(Config.DB_PATH)
    return jsonify({
        "tiene_logo":  info["tiene_logo"],
        "base64":      info["base64"] if info["tiene_logo"] else "",
        "nombre":      info["nombre"],
        "nombre_asoc": info["nombre_asoc"],
        "nit":         info["nit"],
        "municipio":   info["municipio"],
        "correo":      info["correo"],
        "telefono":    info["telefono"],
    })


# ── API Autorizadores ──────────────────────────────────────────────
@auth_bp.route("/configuracion/api/autorizadores")
@login_requerido
def api_get_autorizadores():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM autorizadores ORDER BY orden_firma, activo DESC, nombre"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@auth_bp.route("/configuracion/api/autorizadores", methods=["POST"])
@login_requerido
def api_crear_autorizador():
    data = request.get_json() or {}
    if not data.get("nombre") or not data.get("cargo"):
        return jsonify({"ok": False, "error": "Nombre y cargo requeridos"}), 400
    conn = get_db()
    conn.execute(
        "INSERT INTO autorizadores (nombre,cargo,telefono,email,activo,tipo) VALUES (?,?,?,?,1,'junta')",
        (data["nombre"], data["cargo"],
         data.get("telefono",""), data.get("email",""))
    )
    conn.commit(); conn.close()
    return jsonify({"ok": True}), 201


@auth_bp.route("/configuracion/api/autorizadores/<int:aid>", methods=["PUT"])
@login_requerido
def api_actualizar_autorizador(aid):
    data = request.get_json() or {}
    conn = get_db()
    conn.execute(
        "UPDATE autorizadores SET activo=COALESCE(?,activo), cargo=COALESCE(?,cargo) WHERE id=?",
        (data.get("activo"), data.get("cargo"), aid)
    )
    conn.commit(); conn.close()
    return jsonify({"ok": True})


# ── API Firmas Digitales ──────────────────────────────────────────────
@auth_bp.route("/configuracion/api/firmas")
@login_requerido
def api_get_firmas():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id,nombre,cargo,activo,es_aprobador_formato FROM firmas_digitales ORDER BY nombre"
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@auth_bp.route("/configuracion/api/firmas", methods=["POST"])
@login_requerido
def api_crear_firma():
    nombre = request.form.get("nombre","").strip()
    cargo  = request.form.get("cargo","").strip()
    if not nombre or not cargo:
        return jsonify({"ok": False, "error": "Nombre y cargo requeridos"}), 400
    firma_b64 = None
    if "firma_img" in request.files:
        f = request.files["firma_img"]
        if f.filename:
            raw  = f.read()
            ext  = f.filename.rsplit(".",1)[-1].lower()
            mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"
            firma_b64 = f"data:{mime};base64,{base64.b64encode(raw).decode()}"
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO firmas_digitales (nombre,cargo,firma_base64,activo) VALUES (?,?,?,1)",
            (nombre, cargo, firma_b64)
        )
        conn.commit()
        return jsonify({"ok": True}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@auth_bp.route("/configuracion/api/firmas/<int:fid>", methods=["PUT"])
@login_requerido
def api_toggle_firma(fid):
    data = request.get_json() or {}
    conn = get_db()
    try:
        conn.execute("UPDATE firmas_digitales SET activo=? WHERE id=?",
                     (data.get("activo", 1), fid))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@auth_bp.route("/configuracion/api/firmas/<int:fid>/imagen")
@login_requerido
def api_firma_imagen(fid):
    conn = get_db()
    try:
        r = conn.execute(
            "SELECT firma_base64 FROM firmas_digitales WHERE id=?", (fid,)
        ).fetchone()
        if r and r["firma_base64"]:
            return jsonify({"ok": True, "base64": r["firma_base64"]})
        return jsonify({"ok": False}), 404
    finally:
        conn.close()


# ── API Tipos de Documento (CRUD) ─────────────────────────────────────
@auth_bp.route("/configuracion/api/tipos_documento")
@login_requerido
def api_get_tipos():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id,codigo,nombre,activo FROM tipos_documento ORDER BY nombre"
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@auth_bp.route("/configuracion/api/tipos_documento", methods=["POST"])
@login_requerido
def api_crear_tipo():
    data = request.get_json() or {}
    cod  = data.get("codigo","").strip().upper()
    nom  = data.get("nombre","").strip()
    if not cod or not nom:
        return jsonify({"ok": False, "error": "Código y nombre requeridos"}), 400
    conn = get_db()
    try:
        conn.execute("INSERT INTO tipos_documento (codigo,nombre) VALUES (?,?)", (cod, nom))
        conn.commit()
        return jsonify({"ok": True}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@auth_bp.route("/configuracion/api/tipos_documento/<int:tid>", methods=["PUT"])
@login_requerido
def api_actualizar_tipo(tid):
    data = request.get_json() or {}
    conn = get_db()
    try:
        if "activo" in data:
            conn.execute("UPDATE tipos_documento SET activo=? WHERE id=?",
                         (data["activo"], tid))
        if "nombre" in data:
            conn.execute("UPDATE tipos_documento SET nombre=? WHERE id=?",
                         (data["nombre"].strip(), tid))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@auth_bp.route("/configuracion/api/tipos_documento/<int:tid>", methods=["DELETE"])
@login_requerido
def api_eliminar_tipo(tid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM tipos_documento WHERE id=?", (tid,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


# ── API Aprobador de Formatos ─────────────────────────────────────────
@auth_bp.route("/configuracion/api/aprobador_formato")
@login_requerido
def api_get_aprobador():
    conn = get_db()
    try:
        r = conn.execute("SELECT * FROM config_aprobador_formato WHERE id=1").fetchone()
        return jsonify(dict(r) if r else {})
    finally:
        conn.close()


@auth_bp.route("/configuracion/api/aprobador_formato", methods=["POST"])
@login_requerido
def api_set_aprobador():
    data = request.get_json() or {}
    conn = get_db()
    try:
        conn.execute("""INSERT OR REPLACE INTO config_aprobador_formato
                        (id,nombre,cargo,firma_id,actualizado_en)
                        VALUES (1,?,?,?,datetime('now'))""",
                     (data.get("nombre",""), data.get("cargo",""),
                      data.get("firma_id")))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()
