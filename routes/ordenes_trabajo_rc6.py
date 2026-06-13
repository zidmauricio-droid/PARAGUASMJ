"""
routes/ordenes_trabajo_rc6.py — GA-07 Órdenes de Trabajo (ciclo completo RC6).
"""
import logging
from flask import Blueprint, render_template, request, jsonify, session
from core.database_manager import get_db
from core.seguridad import login_requerido, rol_requerido
from core.auditoria import auditar
from datetime import date

ot_bp = Blueprint("ordenes_trabajo", __name__, url_prefix="/ordenes-trabajo")
_log = logging.getLogger("sigca.ot")


@ot_bp.route("/")
@login_requerido
def panel():
    return render_template("ordenes_trabajo/panel.html")


@ot_bp.route("/api/ot")
@login_requerido
def api_listar():
    estado = request.args.get("estado", "")
    conn   = get_db()
    try:
        sql = """
            SELECT ot.*,
                   c.nombre_completo as suscriptor_nombre,
                   s.codigo_suscriptor
            FROM ordenes_trabajo ot
            LEFT JOIN gc_suscriptores s ON s.pk_suscriptor_id = ot.fk_suscriptor_id
            LEFT JOIN contactos c ON c.pk_contacto_id = s.fk_contacto_id
            WHERE 1=1
        """
        params = []
        if estado:
            sql += " AND ot.estado=?"; params.append(estado)
        sql += " ORDER BY ot.rowid DESC LIMIT 200"
        rows = conn.execute(sql, params).fetchall()
        resumen = {}
        for r in conn.execute(
            "SELECT estado, COUNT(*) as n FROM ordenes_trabajo GROUP BY estado"
        ).fetchall():
            resumen[r["estado"]] = r["n"]
        return jsonify({"ok": True, "ot": [dict(r) for r in rows], "resumen": resumen})
    finally:
        conn.close()


@ot_bp.route("/api/ot", methods=["POST"])
@login_requerido
def api_crear():
    d = request.get_json(silent=True) or {}
    if not d.get("descripcion"):
        return jsonify({"ok": False, "error": "descripcion requerida"})
    conn = get_db()
    try:
        cols = conn.execute("PRAGMA table_info(ordenes_trabajo)").fetchall()
        col_names = {c[1] for c in cols}
        # Construir INSERT dinámico según columnas disponibles
        campos = ["descripcion", "fecha_creacion", "estado", "prioridad"]
        valores = [
            str(d["descripcion"])[:500],
            date.today().isoformat(),
            "CREADA",
            d.get("prioridad", "NORMAL"),
        ]
        for col in ("fk_suscriptor_id", "fk_punto_gis_id", "costo_estimado"):
            if col in col_names and d.get(col) is not None:
                campos.append(col)
                valores.append(d[col])
        placeholders = ",".join(["?"] * len(campos))
        cur = conn.execute(
            f"INSERT INTO ordenes_trabajo ({','.join(campos)}) VALUES ({placeholders})",
            valores
        )
        conn.commit()
        auditar("OT_NUEVA", detalle=f"OT #{cur.lastrowid} creada", modulo="ordenes_trabajo")
        return jsonify({"ok": True, "pk_ot_id": cur.lastrowid})
    except Exception as e:
        conn.rollback()
        _log.error("api_crear OT: %s", e, exc_info=True)
        return jsonify({"ok": False, "error": "Error interno"})
    finally:
        conn.close()


@ot_bp.route("/api/ot/<int:oid>")
@login_requerido
def api_detalle(oid):
    conn = get_db()
    try:
        ot = conn.execute("SELECT * FROM ordenes_trabajo WHERE rowid=?", (oid,)).fetchone()
        if not ot:
            ot = conn.execute("SELECT * FROM ordenes_trabajo WHERE pk_ot_id=?", (oid,)).fetchone()
        if not ot:
            return jsonify({"ok": False, "error": "OT no encontrada"})
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        materiales, imagenes = [], []
        if "ga_ot_materiales" in tablas:
            materiales = [dict(r) for r in conn.execute(
                "SELECT * FROM ga_ot_materiales WHERE fk_ot_id=?", (oid,)
            ).fetchall()]
        if "ga_ot_imagenes" in tablas:
            imagenes = [dict(r) for r in conn.execute(
                "SELECT * FROM ga_ot_imagenes WHERE fk_ot_id=?", (oid,)
            ).fetchall()]
        return jsonify({"ok": True, "ot": dict(ot),
                        "materiales": materiales, "imagenes": imagenes})
    finally:
        conn.close()


@ot_bp.route("/api/ot/<int:oid>/estado", methods=["POST"])
@login_requerido
def api_cambiar_estado(oid):
    d = request.get_json(silent=True) or {}
    nuevo = str(d.get("estado", "")).upper()
    estados_validos = {"CREADA", "ASIGNADA", "EN_EJECUCION", "CERRADA", "CANCELADA"}
    if nuevo not in estados_validos:
        return jsonify({"ok": False, "error": f"Estado inválido: {nuevo}"})
    conn = get_db()
    try:
        conn.execute(
            "UPDATE ordenes_trabajo SET estado=? WHERE pk_ot_id=? OR rowid=?",
            (nuevo, oid, oid)
        )
        conn.commit()
        auditar("OT_ESTADO", detalle=f"OT #{oid} → {nuevo}", modulo="ordenes_trabajo")
        return jsonify({"ok": True})
    finally:
        conn.close()


@ot_bp.route("/api/ot/<int:oid>/materiales", methods=["POST"])
@login_requerido
def api_material(oid):
    d = request.get_json(silent=True) or {}
    if not d.get("descripcion") or not d.get("cantidad"):
        return jsonify({"ok": False, "error": "descripcion y cantidad requeridos"})
    conn = get_db()
    try:
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "ga_ot_materiales" not in tablas:
            return jsonify({"ok": False, "error": "Módulo no inicializado"})
        conn.execute("""
            INSERT INTO ga_ot_materiales
            (fk_ot_id, fk_item_id, descripcion, cantidad, unidad, costo_unitario, fecha_uso)
            VALUES (?,?,?,?,?,?,?)
        """, (oid, d.get("fk_item_id"), str(d["descripcion"])[:200],
              float(d["cantidad"]), d.get("unidad", "und"),
              float(d.get("costo_unitario", 0)),
              d.get("fecha_uso", date.today().isoformat())))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@ot_bp.route("/api/resumen")
@login_requerido
def api_resumen():
    conn = get_db()
    try:
        estados = {}
        for r in conn.execute(
            "SELECT estado, COUNT(*) n FROM ordenes_trabajo GROUP BY estado"
        ).fetchall():
            estados[r["estado"]] = r["n"]
        return jsonify({"ok": True, "estados": estados,
                        "total": sum(estados.values())})
    finally:
        conn.close()
