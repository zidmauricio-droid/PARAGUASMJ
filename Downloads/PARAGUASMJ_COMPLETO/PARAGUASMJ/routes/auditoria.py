"""
routes/auditoria.py
Panel de auditoría (solo admin) + gestión de usuarios con foto.
Fuente: PROGRAMA_3.doc.
"""
import os
from flask import (Blueprint, render_template, request, jsonify,
                   redirect, url_for, flash, session, send_file)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from core.database_manager import get_db
from core.seguridad import login_requerido, rol_requerido
from utils.audit import log_action
from datetime import datetime

aud_bp = Blueprint("auditoria", __name__, url_prefix="/auditoria")

FOTO_DIR   = os.path.join("static", "uploads", "usuarios")
FOTO_EXTS  = {"png", "jpg", "jpeg", "webp", "gif"}


# ── Panel de auditoría ───────────────────────────────────────────────
@aud_bp.route("/")
@login_requerido
@rol_requerido("admin")
def panel():
    return render_template("auditoria/panel.html")


@aud_bp.route("/api/logs")
@login_requerido
@rol_requerido("admin")
def api_logs():
    """Logs paginados con filtros."""
    limit   = min(request.args.get("limit", 100, type=int), 500)
    offset  = request.args.get("offset", 0, type=int)
    buscar  = request.args.get("q", "").strip()
    modulo  = request.args.get("modulo", "")
    accion  = request.args.get("accion", "")
    desde   = request.args.get("desde", "")
    hasta   = request.args.get("hasta", "")

    conn = get_db()
    sql    = "SELECT * FROM audit_log WHERE 1=1"
    params = []
    if buscar:
        sql += " AND (nombre_usuario LIKE ? OR descripcion LIKE ? OR ip_address LIKE ?)"
        params.extend([f"%{buscar}%"]*3)
    if modulo:
        sql += " AND modulo=?"; params.append(modulo)
    if accion:
        sql += " AND accion=?"; params.append(accion)
    if desde:
        sql += " AND timestamp>=?"; params.append(desde)
    if hasta:
        sql += " AND timestamp<=?"; params.append(hasta + " 23:59:59")

    total = conn.execute(f"SELECT COUNT(*) as c FROM ({sql})", params).fetchone()["c"]
    sql  += f" ORDER BY timestamp DESC LIMIT {limit} OFFSET {offset}"
    rows  = conn.execute(sql, params).fetchall()

    modulos = conn.execute("SELECT DISTINCT modulo FROM audit_log ORDER BY modulo").fetchall()
    acciones = conn.execute("SELECT DISTINCT accion FROM audit_log ORDER BY accion").fetchall()
    conn.close()

    return jsonify({
        "total":    total,
        "offset":   offset,
        "limit":    limit,
        "logs":     [dict(r) for r in rows],
        "modulos":  [r["modulo"] for r in modulos],
        "acciones": [r["accion"] for r in acciones],
    })


@aud_bp.route("/api/logs/exportar")
@login_requerido
@rol_requerido("admin")
def exportar_logs():
    """Exporta audit_log a Excel."""
    import pandas as pd
    from io import BytesIO
    conn = get_db()
    rows = conn.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 5000").fetchall()
    conn.close()
    df  = pd.DataFrame([dict(r) for r in rows])
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as wr:
        df.to_excel(wr, sheet_name="AuditLog", index=False)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f"AuditLog_ASUACAP_{datetime.now().strftime('%Y%m%d')}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@aud_bp.route("/api/stats")
@login_requerido
@rol_requerido("admin")
def api_stats():
    """Estadísticas de auditoría para el dashboard."""
    conn = get_db()
    total_hoy = conn.execute(
        "SELECT COUNT(*) as c FROM audit_log WHERE date(timestamp)=date('now')"
    ).fetchone()["c"]
    por_modulo = conn.execute("""
        SELECT modulo, COUNT(*) as c FROM audit_log
        WHERE timestamp >= datetime('now','-7 days')
        GROUP BY modulo ORDER BY c DESC
    """).fetchall()
    por_accion = conn.execute("""
        SELECT accion, COUNT(*) as c FROM audit_log
        WHERE timestamp >= datetime('now','-7 days')
        GROUP BY accion ORDER BY c DESC LIMIT 10
    """).fetchall()
    logins_fallidos = conn.execute("""
        SELECT COUNT(*) as c FROM audit_log
        WHERE accion='LOGIN_FAILED' AND timestamp >= datetime('now','-24 hours')
    """).fetchone()["c"]
    conn.close()
    return jsonify({
        "total_hoy":      total_hoy,
        "por_modulo":     [dict(r) for r in por_modulo],
        "por_accion":     [dict(r) for r in por_accion],
        "logins_fallidos": logins_fallidos,
    })


# ── Gestión de usuarios (PROGRAMA_3) ────────────────────────────────
@aud_bp.route("/usuarios")
@login_requerido
@rol_requerido("admin")
def usuarios():
    return render_template("auditoria/usuarios.html")


@aud_bp.route("/api/usuarios")
@login_requerido
@rol_requerido("admin")
def api_listar_usuarios():
    conn = get_db()
    rows = conn.execute("""
        SELECT pk_usuario_id, nombre_completo, nombre_usuario, rol, correo,
               telefono, activo, ultimo_acceso, fecha_creacion,
               COALESCE(foto_path,'') as foto_path,
               COALESCE(bloqueado,0) as bloqueado,
               COALESCE(intentos_fallidos,0) as intentos_fallidos
        FROM usuarios ORDER BY nombre_completo
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@aud_bp.route("/api/usuarios", methods=["POST"])
@login_requerido
@rol_requerido("admin")
def api_crear_usuario():
    nombre   = request.form.get("nombre_completo","").strip()
    usuario  = request.form.get("nombre_usuario","").strip()
    clave    = request.form.get("password","")
    rol      = request.form.get("rol","auxiliar")
    correo   = request.form.get("correo","")
    telefono = request.form.get("telefono","")
    foto     = request.files.get("foto")

    if not nombre or not usuario or not clave:
        return jsonify({"ok": False, "error": "Nombre, usuario y clave son obligatorios"}), 400

    foto_path = None
    if foto and foto.filename:
        ext = foto.filename.rsplit(".",1)[-1].lower()
        if ext in FOTO_EXTS:
            os.makedirs(FOTO_DIR, exist_ok=True)
            fn = secure_filename(f"usr_{usuario}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}")
            foto.save(os.path.join(FOTO_DIR, fn))
            foto_path = f"/static/uploads/usuarios/{fn}"

    conn = get_db()
    try:
        if conn.execute("SELECT 1 FROM usuarios WHERE nombre_usuario=?",(usuario,)).fetchone():
            conn.close()
            return jsonify({"ok": False, "error": "El nombre de usuario ya existe"}), 409
        conn.execute("""
            INSERT INTO usuarios (nombre_completo,nombre_usuario,password_hash,rol,correo,telefono,foto_path,activo)
            VALUES (?,?,?,?,?,?,?,1)
        """,(nombre, usuario, generate_password_hash(clave), rol, correo, telefono, foto_path))
        conn.commit()
        uid = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
        log_action(accion="CREATE_USER", modulo="usuarios",
                   descripcion=f"Usuario creado: {usuario} ({rol})")
        conn.close()
        return jsonify({"ok": True, "id": uid})
    except Exception as e:
        conn.rollback(); conn.close()
        return jsonify({"ok": False, "error": str(e)}), 500


@aud_bp.route("/api/usuarios/<int:uid>", methods=["PUT"])
@login_requerido
@rol_requerido("admin")
def api_editar_usuario(uid):
    nombre   = request.form.get("nombre_completo","").strip()
    rol      = request.form.get("rol","")
    correo   = request.form.get("correo","")
    telefono = request.form.get("telefono","")
    activo   = request.form.get("activo","1")
    nueva_clave = request.form.get("password","")
    foto     = request.files.get("foto")

    conn = get_db()
    try:
        foto_path = None
        if foto and foto.filename:
            ext = foto.filename.rsplit(".",1)[-1].lower()
            if ext in FOTO_EXTS:
                os.makedirs(FOTO_DIR, exist_ok=True)
                fn = secure_filename(f"usr_{uid}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}")
                foto.save(os.path.join(FOTO_DIR, fn))
                foto_path = f"/static/uploads/usuarios/{fn}"

        updates = ["nombre_completo=?","correo=?","telefono=?","activo=?","rol=?"]
        params  = [nombre, correo, telefono, int(activo), rol]
        if nueva_clave:
            updates.append("password_hash=?")
            params.append(generate_password_hash(nueva_clave))
        if foto_path:
            updates.append("foto_path=?")
            params.append(foto_path)
        params.append(uid)
        conn.execute(f"UPDATE usuarios SET {','.join(updates)} WHERE pk_usuario_id=?", params)
        conn.commit()
        log_action(accion="UPDATE_USER", modulo="usuarios",
                   descripcion=f"Usuario {uid} editado")
        conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        conn.rollback(); conn.close()
        return jsonify({"ok": False, "error": str(e)}), 500


@aud_bp.route("/api/usuarios/<int:uid>/desbloquear", methods=["POST"])
@login_requerido
@rol_requerido("admin")
def api_desbloquear(uid):
    conn = get_db()
    conn.execute("UPDATE usuarios SET bloqueado=0,intentos_fallidos=0 WHERE pk_usuario_id=?", (uid,))
    conn.commit(); conn.close()
    log_action(accion="UNBLOCK_USER", modulo="usuarios", descripcion=f"Usuario {uid} desbloqueado")
    return jsonify({"ok": True})


@aud_bp.route("/api/usuarios/<int:uid>", methods=["DELETE"])
@login_requerido
@rol_requerido("admin")
def api_eliminar_usuario(uid):
    if uid == session.get("usuario_id"):
        return jsonify({"ok": False, "error": "No puede eliminarse a sí mismo"}), 403
    conn = get_db()
    u = conn.execute("SELECT rol FROM usuarios WHERE pk_usuario_id=?", (uid,)).fetchone()
    if u and u["rol"] == "admin":
        admins = conn.execute("SELECT COUNT(*) as c FROM usuarios WHERE rol='admin' AND activo=1").fetchone()["c"]
        if admins <= 1:
            conn.close()
            return jsonify({"ok": False, "error": "No puede eliminar el único administrador"}), 403
    conn.execute("UPDATE usuarios SET activo=0 WHERE pk_usuario_id=?", (uid,))
    conn.commit()
    log_action(accion="DELETE_USER", modulo="usuarios", descripcion=f"Usuario {uid} desactivado")
    conn.close()
    return jsonify({"ok": True})
