"""
routes/laboral.py — GL-01 Personal básico.
"""
import logging
from flask import Blueprint, render_template, request, jsonify, session
from core.database_manager import get_db
from core.seguridad import login_requerido, rol_requerido

lab_bp = Blueprint("laboral", __name__, url_prefix="/laboral")
_log   = logging.getLogger("sigca.laboral")


@lab_bp.route("/")
@login_requerido
def panel():
    return render_template("laboral/panel.html")


@lab_bp.route("/api/personal")
@login_requerido
def api_listar():
    estado = request.args.get("estado", "ACTIVO")
    conn   = get_db()
    try:
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "gl_personal" not in tablas:
            return jsonify({"ok": False, "error": "Módulo no inicializado"})
        sql = """
            SELECT p.*, c.nombre_completo, c.email, c.telefono
            FROM gl_personal p
            LEFT JOIN contactos c ON c.pk_contacto_id = p.fk_contacto_id
            WHERE p.estado=?
            ORDER BY c.nombre_completo
        """
        rows = conn.execute(sql, (estado,)).fetchall()
        return jsonify({"ok": True, "personal": [dict(r) for r in rows],
                        "total": len(rows)})
    finally:
        conn.close()


@lab_bp.route("/api/personal", methods=["POST"])
@login_requerido
@rol_requerido("admin", "presidente")
def api_crear():
    d = request.get_json(silent=True) or {}
    if not d.get("cargo"):
        return jsonify({"ok": False, "error": "cargo requerido"})
    conn = get_db()
    try:
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "gl_personal" not in tablas:
            return jsonify({"ok": False, "error": "Módulo no inicializado"})
        cur = conn.execute("""
            INSERT INTO gl_personal
            (fk_contacto_id, cargo, tipo_contrato, fecha_ingreso,
             salario_base, estado, numero_contrato, eps, arl, fondo_pension,
             observaciones, usuario)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            d.get("fk_contacto_id"),
            str(d["cargo"])[:100],
            d.get("tipo_contrato", "TERMINO_INDEFINIDO"),
            d.get("fecha_ingreso", ""),
            float(d.get("salario_base", 0)),
            d.get("estado", "ACTIVO"),
            d.get("numero_contrato", ""),
            d.get("eps", ""), d.get("arl", ""), d.get("fondo_pension", ""),
            d.get("observaciones", ""),
            session.get("nombre_usuario", "anonimo"),
        ))
        conn.commit()
        return jsonify({"ok": True, "pk_personal_id": cur.lastrowid})
    except Exception as e:
        conn.rollback()
        _log.error("api_crear personal: %s", e)
        return jsonify({"ok": False, "error": "Error interno"})
    finally:
        conn.close()


@lab_bp.route("/api/personal/<int:pid>", methods=["PUT"])
@login_requerido
@rol_requerido("admin", "presidente")
def api_actualizar(pid):
    d = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        permitidos = {"cargo", "tipo_contrato", "fecha_retiro", "salario_base",
                      "estado", "eps", "arl", "fondo_pension", "observaciones"}
        sets, params = [], []
        for k, v in d.items():
            if k in permitidos:
                sets.append(f"{k}=?"); params.append(v)
        if not sets:
            return jsonify({"ok": False, "error": "Sin campos"})
        params.append(pid)
        conn.execute(f"UPDATE gl_personal SET {','.join(sets)} WHERE pk_personal_id=?", params)
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()
