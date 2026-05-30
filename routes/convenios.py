"""
PARAGUASMJ — Módulo Convenios y Contratos
Arquitectura: Convenios → Contratos → Proyectos → Actividades → Finanzas
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from core.database_manager import get_db
from core.seguridad import login_requerido
import logging

conv_bp = Blueprint("convenios", __name__, url_prefix="/convenios")
logger  = logging.getLogger("paraguasmj")


# ── Panel principal ──────────────────────────────────────────────────
@conv_bp.route("/")
@login_requerido
def panel():
    conn = get_db()
    try:
        convenios = conn.execute("""
            SELECT c.*,
                   COUNT(DISTINCT p.pk_proyecto_id) AS total_proyectos,
                   COALESCE(SUM(p.valor_ejecutado),0) AS total_ejecutado
            FROM convenios c
            LEFT JOIN proyectos p ON p.fk_convenio_id = c.pk_convenio_id
            GROUP BY c.pk_convenio_id
            ORDER BY c.creado_en DESC
        """).fetchall()
        stats = {
            "total":     conn.execute("SELECT COUNT(*) FROM convenios").fetchone()[0],
            "activos":   conn.execute("SELECT COUNT(*) FROM convenios WHERE estado='activo'").fetchone()[0],
            "valor":     conn.execute("SELECT COALESCE(SUM(valor_aprobado),0) FROM convenios").fetchone()[0],
        }
    finally:
        conn.close()
    return render_template("convenios/panel.html", convenios=convenios, stats=stats)


# ── Detalle de convenio ──────────────────────────────────────────────
@conv_bp.route("/<int:cid>")
@login_requerido
def detalle(cid):
    conn = get_db()
    try:
        conv = conn.execute(
            "SELECT * FROM convenios WHERE pk_convenio_id=?", (cid,)
        ).fetchone()
        if not conv:
            flash("Convenio no encontrado.", "warning")
            return redirect(url_for("convenios.panel"))
        proyectos = conn.execute(
            "SELECT * FROM proyectos WHERE fk_convenio_id=? ORDER BY creado_en DESC", (cid,)
        ).fetchall()
        contratos = conn.execute(
            "SELECT * FROM contratos WHERE fk_convenio_id=? ORDER BY creado_en DESC", (cid,)
        ).fetchall()
    finally:
        conn.close()
    return render_template("convenios/detalle.html",
                           conv=conv, proyectos=proyectos, contratos=contratos)


# ── API: CRUD convenios ──────────────────────────────────────────────
@conv_bp.route("/api/listar")
@login_requerido
def api_listar():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT c.*, COUNT(DISTINCT p.pk_proyecto_id) as proyectos
            FROM convenios c
            LEFT JOIN proyectos p ON p.fk_convenio_id=c.pk_convenio_id
            GROUP BY c.pk_convenio_id ORDER BY c.creado_en DESC
        """).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@conv_bp.route("/api/crear", methods=["POST"])
@login_requerido
def api_crear():
    d = request.get_json(silent=True) or {}
    required = ["codigo", "nombre"]
    if not all(d.get(k,"").strip() for k in required):
        return jsonify({"ok": False, "error": "Código y nombre son obligatorios"}), 400
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO convenios
            (codigo,nombre,entidad_financiadora,objeto,valor_aprobado,
             fecha_inicio,fecha_fin,estado,creado_por)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            d["codigo"].strip().upper(),
            d["nombre"].strip(),
            d.get("entidad_financiadora",""),
            d.get("objeto",""),
            float(d.get("valor_aprobado") or 0),
            d.get("fecha_inicio",""),
            d.get("fecha_fin",""),
            d.get("estado","activo"),
            session.get("nombre_usuario","sistema"),
        ))
        conn.commit()
        nid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        logger.info(f"Convenio creado: {d['codigo']} por {session.get('nombre_usuario')}")
        return jsonify({"ok": True, "id": nid})
    except Exception as e:
        conn.rollback()
        if "UNIQUE constraint" in str(e):
            return jsonify({"ok": False, "error": f"Ya existe el código {d['codigo']}"}), 409
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@conv_bp.route("/api/<int:cid>", methods=["PUT"])
@login_requerido
def api_actualizar(cid):
    d = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        conn.execute("""
            UPDATE convenios SET
              nombre=?, entidad_financiadora=?, objeto=?,
              valor_aprobado=?, fecha_inicio=?, fecha_fin=?, estado=?
            WHERE pk_convenio_id=?
        """, (
            d.get("nombre",""),
            d.get("entidad_financiadora",""),
            d.get("objeto",""),
            float(d.get("valor_aprobado") or 0),
            d.get("fecha_inicio",""),
            d.get("fecha_fin",""),
            d.get("estado","activo"),
            cid,
        ))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


# ── API: Contratos ────────────────────────────────────────────────────
@conv_bp.route("/api/<int:cid>/contratos")
@login_requerido
def api_contratos(cid):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM contratos WHERE fk_convenio_id=? ORDER BY creado_en DESC", (cid,)
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@conv_bp.route("/api/contrato/crear", methods=["POST"])
@login_requerido
def api_contrato_crear():
    d = request.get_json(silent=True) or {}
    if not d.get("fk_convenio_id") or not d.get("numero","").strip():
        return jsonify({"ok": False, "error": "Convenio y número de contrato requeridos"}), 400
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO contratos
            (fk_convenio_id,numero,tipo,contratista,objeto,valor,plazo_meses,fecha_inicio,fecha_fin,estado)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            d["fk_convenio_id"], d["numero"].strip().upper(),
            d.get("tipo",""), d.get("contratista",""),
            d.get("objeto",""), float(d.get("valor") or 0),
            int(d.get("plazo_meses") or 0),
            d.get("fecha_inicio",""), d.get("fecha_fin",""),
            d.get("estado","activo"),
        ))
        conn.commit()
        nid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return jsonify({"ok": True, "id": nid})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@conv_bp.route("/api/contrato/<int:tid>/adicion", methods=["POST"])
@login_requerido
def api_adicion(tid):
    d = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO adiciones(fk_contrato_id,monto_adicionado,motivo,fecha_aprobacion) VALUES(?,?,?,?)",
            (tid, float(d.get("monto",0)), d.get("motivo",""), d.get("fecha",""))
        )
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@conv_bp.route("/api/contrato/<int:tid>/prorroga", methods=["POST"])
@login_requerido
def api_prorroga(tid):
    d = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO prorrogas(fk_contrato_id,nueva_fecha_fin,justificacion) VALUES(?,?,?)",
            (tid, d.get("nueva_fecha_fin",""), d.get("justificacion",""))
        )
        conn.execute(
            "UPDATE contratos SET fecha_fin=?, estado='prorrogado' WHERE pk_contrato_id=?",
            (d.get("nueva_fecha_fin",""), tid)
        )
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()
