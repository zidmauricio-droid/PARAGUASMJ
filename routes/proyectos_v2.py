"""
routes/proyectos_v2.py
Módulo de proyectos PUEAA/PSMV/Obras — con Gantt, documentos asociados,
metas con soporte documental, informe de avance Excel.
PROGRAMA_4 + PROGRAMA_5 integrados.

Schema real BD:
  proyectos: pk_proyecto_id, codigo, nombre, descripcion, responsable_id,
             presupuesto, valor_ejecutado, fecha_inicio, fecha_limite,
             fecha_real_fin, porcentaje_completado, estado, performance,
             comentarios, fecha_creacion, objetivo, tipo_proyecto,
             ingresos_totales, creado_por, actualizado_en
  tareas_proyecto: id, proyecto_id, nombre, descripcion, prioridad, estado,
                   fecha_inicio_plan, fecha_fin_plan, porcentaje_avance,
                   responsable_id, costo_estimado, costo_real, orden, creado_en
"""
import os
import sqlite3
import logging
import time
from functools import wraps
from flask import (Blueprint, render_template, request, jsonify,
                   session, send_file)
from core.database_manager import get_db
from core.seguridad import login_requerido
from utils.audit import log_action
from datetime import datetime
from io import BytesIO

proy2_bp = Blueprint("proyectos2", __name__, url_prefix="/proyectos2")

logger = logging.getLogger("asuacap.proyectos2")


def with_retry(max_retries: int = 3, base_delay: float = 0.25):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    last_exception = e
                    if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                        import time as _t; _t.sleep(base_delay * (2 ** attempt))
                        continue
                    break
                except Exception:
                    raise
            raise last_exception
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════
# EVIDENCIAS DEL PROYECTO
# ═══════════════════════════════════════════════════════
@proy2_bp.route("/api/<int:pid>/evidencias", methods=["GET"])
@login_requerido
def api_listar_evidencias(pid):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT e.*, u.nombre_completo as subido_por_nombre
            FROM evidencias_proyecto e
            LEFT JOIN usuarios u ON e.subido_por = u.pk_usuario_id
            WHERE e.proyecto_id = ? ORDER BY e.fecha_subida DESC
        """, (pid,)).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@proy2_bp.route("/api/<int:pid>/evidencias", methods=["POST"])
@login_requerido
@with_retry()
def api_subir_evidencia(pid):
    from werkzeug.utils import secure_filename
    import os
    if 'archivo' not in request.files:
        return jsonify({"ok": False, "error": "Sin archivo"}), 400
    archivo = request.files['archivo']
    if not archivo.filename:
        return jsonify({"ok": False, "error": "Archivo vacío"}), 400
    ext = archivo.filename.rsplit(".",1)[-1].lower() if "." in archivo.filename else ""
    if ext not in {"pdf","jpg","jpeg","png","doc","docx","xls","xlsx"}:
        return jsonify({"ok": False, "error": "Formato no permitido"}), 400
    UPLOAD = os.path.join("uploads","evidencias_proyectos")
    os.makedirs(UPLOAD, exist_ok=True)
    fn = secure_filename(f"PRY-{pid}-{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}")
    ruta = os.path.join(UPLOAD, fn)
    archivo.save(ruta)
    conn = get_db()
    try:
        cur = conn.execute("""
            INSERT INTO evidencias_proyecto
            (proyecto_id, nombre_archivo, ruta, descripcion, subido_por)
            VALUES (?,?,?,?,?)
        """, (pid, fn, ruta, request.form.get("descripcion",""), session.get("usuario_id")))
        conn.commit()
        log_action("UPLOAD_EVIDENCIA","proyectos2",f"Proyecto {pid} — {fn}")
        return jsonify({"ok": True, "id": cur.lastrowid}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()

# proyectos2 blueprint definido arriba


def _recalcular_avance(conn, proyecto_id: int):
    """Promedio ponderado de avance de tareas → porcentaje_completado del proyecto."""
    r = conn.execute(
        "SELECT AVG(CAST(porcentaje_avance AS REAL)) as avg "
        "FROM tareas_proyecto WHERE proyecto_id=?",
        (proyecto_id,)
    ).fetchone()
    avance = round(r["avg"] or 0)
    conn.execute(
        "UPDATE proyectos SET porcentaje_completado=?, actualizado_en=? "
        "WHERE pk_proyecto_id=?",
        (avance, datetime.now().isoformat(), proyecto_id)
    )


# ── Panel HTML ────────────────────────────────────────────────────────


# ── Decorador reintentos ─────────────────────────────────────────
def with_retry(max_retries: int = 3, base_delay: float = 0.25):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    last_exc = e
                    if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                        time.sleep(base_delay * (2 ** attempt))
                        continue
                    break
                except Exception:
                    raise
            raise last_exc
        return wrapper
    return decorator

@proy2_bp.route("/")
@login_requerido
def panel():
    return render_template("proyectos2/panel.html")


# ═══════════════════════════════════════════════════════════════════════
# PROYECTOS — CRUD
# ═══════════════════════════════════════════════════════════════════════

@proy2_bp.route("/api", methods=["GET"])
@login_requerido
def api_listar():
    estado = request.args.get("estado", "")
    tipo   = request.args.get("tipo",   "")
    conn   = get_db()
    sql = """
        SELECT p.pk_proyecto_id as id,
               p.codigo, p.nombre, p.descripcion, p.tipo_proyecto,
               p.estado, p.presupuesto as presupuesto_total,
               p.valor_ejecutado as costo_real,
               COALESCE(p.ingresos_totales, 0) as ingresos_totales,
               p.porcentaje_completado as porcentaje_avance,
               p.fecha_inicio as fecha_inicio_plan,
               p.fecha_limite as fecha_fin_plan,
               p.responsable_id, p.objetivo,
               (SELECT nombre_completo FROM usuarios
                WHERE pk_usuario_id=p.responsable_id) as responsable_nombre,
               (SELECT COUNT(*) FROM tareas_proyecto
                WHERE proyecto_id=p.pk_proyecto_id) as total_tareas,
               (SELECT COUNT(*) FROM tareas_proyecto
                WHERE proyecto_id=p.pk_proyecto_id
                  AND estado='completada') as tareas_ok
        FROM proyectos p WHERE 1=1
    """
    params = []
    if estado and estado != "todos":
        sql += " AND p.estado=?"; params.append(estado)
    if tipo and tipo != "todos":
        sql += " AND p.tipo_proyecto=?"; params.append(tipo)
    sql += " ORDER BY p.pk_proyecto_id DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@proy2_bp.route("/api", methods=["POST"])
@login_requerido
def api_crear():
    data = request.get_json() or {}
    if not data.get("nombre"):
        return jsonify({"ok": False, "error": "Nombre obligatorio"}), 400
    conn = get_db()
    anio   = datetime.now().year
    n      = conn.execute("SELECT COUNT(*) as c FROM proyectos").fetchone()["c"]
    codigo = data.get("codigo") or f"PRY-{anio}-{n+1:04d}"
    try:
        cur = conn.execute("""
            INSERT INTO proyectos
            (codigo, nombre, descripcion, objetivo, tipo_proyecto, estado,
             fecha_inicio, fecha_limite, presupuesto, valor_ejecutado,
             ingresos_totales, porcentaje_completado, responsable_id,
             creado_por, fecha_creacion)
            VALUES (?,?,?,?,?,?,?,?,?,0,0,0,?,?,?)
        """, (
            codigo, data["nombre"], data.get("descripcion",""),
            data.get("objetivo",""), data.get("tipo_proyecto","otro"),
            data.get("estado","planificacion"),
            data.get("fecha_inicio_plan"), data.get("fecha_fin_plan"),
            float(data.get("presupuesto_total", 0)),
            data.get("responsable_id"), session.get("usuario_id"),
            datetime.now().isoformat()
        ))
        conn.commit()
        pid = cur.lastrowid
        log_action(accion="CREATE", modulo="proyectos",
                   descripcion=f"Proyecto creado: {codigo}")
        conn.close()
        return jsonify({"ok": True, "id": pid, "codigo": codigo}), 201
    except Exception as e:
        conn.rollback(); conn.close()
        return jsonify({"ok": False, "error": str(e)}), 500


@proy2_bp.route("/api/<int:pid>", methods=["GET"])
@login_requerido
def api_obtener(pid):
    conn = get_db()
    proy = conn.execute("""
        SELECT p.pk_proyecto_id as id, p.codigo, p.nombre, p.descripcion,
               p.tipo_proyecto, p.estado,
               p.presupuesto as presupuesto_total,
               p.valor_ejecutado as costo_real,
               COALESCE(p.ingresos_totales,0) as ingresos_totales,
               p.porcentaje_completado as porcentaje_avance,
               p.fecha_inicio as fecha_inicio_plan,
               p.fecha_limite as fecha_fin_plan,
               p.fecha_real_fin, p.responsable_id,
               p.objetivo, p.comentarios,
               (SELECT nombre_completo FROM usuarios
                WHERE pk_usuario_id=p.responsable_id) as responsable_nombre
        FROM proyectos p WHERE p.pk_proyecto_id=?
    """, (pid,)).fetchone()
    if not proy:
        conn.close()
        return jsonify({"error": "No encontrado"}), 404

    tareas   = conn.execute(
        "SELECT * FROM tareas_proyecto WHERE proyecto_id=? ORDER BY orden,id",
        (pid,)).fetchall()
    costos   = conn.execute(
        "SELECT * FROM costos_reales WHERE proyecto_id=? ORDER BY fecha DESC",
        (pid,)).fetchall()
    ingresos = conn.execute(
        "SELECT * FROM ingresos WHERE proyecto_id=? ORDER BY fecha DESC",
        (pid,)).fetchall()
    riesgos  = conn.execute(
        "SELECT * FROM riesgos_proyecto WHERE proyecto_id=? ORDER BY id",
        (pid,)).fetchall()
    metas    = conn.execute(
        "SELECT * FROM metas_proyecto WHERE proyecto_id=? ORDER BY anio,semestre",
        (pid,)).fetchall()
    deps     = conn.execute("""
        SELECT d.* FROM dependencias d
        JOIN tareas_proyecto t ON d.tarea_id=t.id
        WHERE t.proyecto_id=?
    """, (pid,)).fetchall()
    # PROGRAMA_5: documentos asociados al proyecto
    docs_proy = conn.execute("""
        SELECT dp.id as rel_id, dp.tipo_relacion, dp.observaciones,
               r.pk_registro_id as id, r.codigo_completo as codigo,
               r.asunto_resumen as asunto, r.fecha_radicacion as fecha,
               r.estado
        FROM documentos_proyecto dp
        JOIN registro_central r ON dp.documento_id=r.pk_registro_id
        WHERE dp.proyecto_id=?
        ORDER BY r.fecha_radicacion DESC
    """, (pid,)).fetchall()

    conn.close()
    return jsonify({
        "proyecto":     dict(proy),
        "tareas":       [dict(t) for t in tareas],
        "costos":       [dict(c) for c in costos],
        "ingresos":     [dict(i) for i in ingresos],
        "riesgos":      [dict(r) for r in riesgos],
        "metas":        [dict(m) for m in metas],
        "dependencias": [dict(d) for d in deps],
        "documentos":   [dict(d) for d in docs_proy],
    })


@proy2_bp.route("/api/<int:pid>", methods=["PUT"])
@login_requerido
def api_actualizar(pid):
    data = request.get_json() or {}
    mapa = {
        "nombre": "nombre", "descripcion": "descripcion",
        "objetivo": "objetivo", "tipo_proyecto": "tipo_proyecto",
        "estado": "estado",
        "fecha_inicio_plan": "fecha_inicio",
        "fecha_fin_plan":    "fecha_limite",
        "fecha_fin_real":    "fecha_real_fin",
        "presupuesto_total": "presupuesto",
        "responsable_id":    "responsable_id",
    }
    sets, params = [], []
    for k, col in mapa.items():
        if k in data:
            sets.append(f"{col}=?"); params.append(data[k])
    if not sets:
        return jsonify({"ok": False, "error": "Sin campos"}), 400
    sets.append("actualizado_en=?"); params.append(datetime.now().isoformat())
    params.append(pid)
    conn = get_db()
    conn.execute(f"UPDATE proyectos SET {','.join(sets)} WHERE pk_proyecto_id=?",
                 params)
    conn.commit(); conn.close()
    log_action(accion="UPDATE", modulo="proyectos",
               descripcion=f"Proyecto {pid} actualizado")
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════════════════
# TAREAS
# ═══════════════════════════════════════════════════════════════════════

@proy2_bp.route("/api/<int:pid>/tareas", methods=["POST"])
@login_requerido
def api_crear_tarea(pid):
    data = request.get_json() or {}
    if not data.get("nombre"):
        return jsonify({"ok": False, "error": "Nombre requerido"}), 400
    conn = get_db()
    cur  = conn.execute("""
        INSERT INTO tareas_proyecto
        (proyecto_id, nombre, descripcion, prioridad, estado,
         fecha_inicio_plan, fecha_fin_plan, duracion_estimada_dias,
         responsable_id, costo_estimado, orden, creado_en)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (pid, data["nombre"], data.get("descripcion",""),
          data.get("prioridad","media"), data.get("estado","pendiente"),
          data.get("fecha_inicio_plan"), data.get("fecha_fin_plan"),
          data.get("duracion_estimada_dias"),
          data.get("responsable_id"),
          float(data.get("costo_estimado",0)),
          data.get("orden",0), datetime.now().isoformat()))
    conn.commit(); tid = cur.lastrowid
    log_action(accion="CREATE_TASK", modulo="proyectos",
               descripcion=f"Tarea '{data['nombre']}' en proyecto {pid}")
    conn.close()
    return jsonify({"ok": True, "id": tid}), 201


@proy2_bp.route("/api/tareas/<int:tid>", methods=["PUT"])
@login_requerido
def api_actualizar_tarea(tid):
    data  = request.get_json() or {}
    conn  = get_db()
    tarea = conn.execute(
        "SELECT proyecto_id FROM tareas_proyecto WHERE id=?", (tid,)
    ).fetchone()
    if not tarea:
        conn.close(); return jsonify({"ok": False}), 404

    campos = ["nombre","descripcion","prioridad","estado",
              "fecha_inicio_plan","fecha_fin_plan","fecha_inicio_real","fecha_fin_real",
              "duracion_estimada_dias","porcentaje_avance","responsable_id",
              "costo_estimado","costo_real","orden"]
    sets, params = [], []
    for c in campos:
        if c in data:
            sets.append(f"{c}=?"); params.append(data[c])
    if sets:
        params.append(tid)
        conn.execute(f"UPDATE tareas_proyecto SET {','.join(sets)} WHERE id=?",
                     params)
        conn.commit()
        _recalcular_avance(conn, tarea["proyecto_id"])
        conn.commit()
    conn.close()
    return jsonify({"ok": True})


@proy2_bp.route("/api/tareas/<int:tid>", methods=["DELETE"])
@login_requerido
def api_eliminar_tarea(tid):
    conn = get_db()
    conn.execute("DELETE FROM tareas_proyecto WHERE id=?", (tid,))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════════════════
# GANTT
# ═══════════════════════════════════════════════════════════════════════

@proy2_bp.route("/api/<int:pid>/gantt", methods=["GET"])
@login_requerido
def api_gantt(pid):
    conn = get_db()
    tareas = conn.execute("""
        SELECT id, nombre as text,
               COALESCE(fecha_inicio_plan, date('now'))           as start_date,
               COALESCE(fecha_fin_plan,    date('now','+7 days')) as end_date,
               COALESCE(duracion_estimada_dias, 7)                as duration,
               CAST(COALESCE(porcentaje_avance,0) AS REAL)/100.0  as progress,
               padre_id, estado, prioridad
        FROM tareas_proyecto WHERE proyecto_id=? ORDER BY orden,id
    """, (pid,)).fetchall()
    deps = conn.execute("""
        SELECT d.tarea_id as source, d.tarea_dependiente_id as target, d.tipo
        FROM dependencias d
        JOIN tareas_proyecto t ON d.tarea_id=t.id
        WHERE t.proyecto_id=?
    """, (pid,)).fetchall()
    conn.close()
    return jsonify({
        "data":  [dict(t) for t in tareas],
        "links": [{"id": i, "source": str(d["source"]),
                   "target": str(d["target"]), "type": d["tipo"]}
                  for i, d in enumerate(deps)],
    })


# ═══════════════════════════════════════════════════════════════════════
# COSTOS E INGRESOS
# ═══════════════════════════════════════════════════════════════════════

@proy2_bp.route("/api/<int:pid>/costos", methods=["POST"])
@login_requerido
def api_costo(pid):
    data  = request.get_json() or {}
    monto = float(data.get("monto", 0))
    if not data.get("concepto") or monto <= 0:
        return jsonify({"ok": False, "error": "Concepto y monto requeridos"}), 400
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO costos_reales
        (proyecto_id, tarea_id, fecha, concepto, monto, comprobante,
         registrado_por, creado_en)
        VALUES (?,?,?,?,?,?,?,?)
    """, (pid, data.get("tarea_id"),
          data.get("fecha", datetime.now().date().isoformat()),
          data["concepto"], monto, data.get("comprobante"),
          session.get("usuario_id"), datetime.now().isoformat()))
    if data.get("tarea_id"):
        conn.execute("UPDATE tareas_proyecto SET costo_real=costo_real+? WHERE id=?",
                     (monto, data["tarea_id"]))
    conn.execute(
        "UPDATE proyectos SET valor_ejecutado=valor_ejecutado+?,actualizado_en=? "
        "WHERE pk_proyecto_id=?",
        (monto, datetime.now().isoformat(), pid)
    )
    conn.commit()
    log_action(accion="CREATE_COST", modulo="proyectos",
               descripcion=f"Costo ${monto:,.0f} en proyecto {pid}")
    conn.close()
    return jsonify({"ok": True, "id": cur.lastrowid}), 201


@proy2_bp.route("/api/<int:pid>/ingresos", methods=["POST"])
@login_requerido
def api_ingreso(pid):
    data  = request.get_json() or {}
    monto = float(data.get("monto", 0))
    if not data.get("fuente") or monto <= 0:
        return jsonify({"ok": False, "error": "Fuente y monto requeridos"}), 400
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO ingresos
        (proyecto_id, fecha, fuente, concepto, monto, comprobante, registrado_por)
        VALUES (?,?,?,?,?,?,?)
    """, (pid, data.get("fecha", datetime.now().date().isoformat()),
          data["fuente"], data.get("concepto",""),
          monto, data.get("comprobante"), session.get("usuario_id")))
    conn.execute(
        "UPDATE proyectos SET ingresos_totales=ingresos_totales+?,actualizado_en=? "
        "WHERE pk_proyecto_id=?",
        (monto, datetime.now().isoformat(), pid)
    )
    conn.commit(); conn.close()
    return jsonify({"ok": True, "id": cur.lastrowid}), 201


# ═══════════════════════════════════════════════════════════════════════
# RIESGOS
# ═══════════════════════════════════════════════════════════════════════

@proy2_bp.route("/api/<int:pid>/riesgos", methods=["POST"])
@login_requerido
def api_riesgo(pid):
    data = request.get_json() or {}
    conn = get_db()
    cur  = conn.execute("""
        INSERT INTO riesgos_proyecto
        (proyecto_id, nombre, descripcion, probabilidad, impacto,
         plan_mitigacion, responsable_id, estado, creado_en)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (pid, data.get("nombre","Riesgo"), data.get("descripcion",""),
          data.get("probabilidad","media"), data.get("impacto","medio"),
          data.get("plan_mitigacion",""), data.get("responsable_id"),
          data.get("estado","identificado"), datetime.now().isoformat()))
    conn.commit(); conn.close()
    return jsonify({"ok": True, "id": cur.lastrowid}), 201


@proy2_bp.route("/api/riesgos/<int:rid>", methods=["PUT"])
@login_requerido
def api_actualizar_riesgo(rid):
    data = request.get_json() or {}
    conn = get_db()
    conn.execute(
        "UPDATE riesgos_proyecto SET estado=?,plan_mitigacion=? WHERE id=?",
        (data.get("estado","identificado"), data.get("plan_mitigacion",""), rid)
    )
    conn.commit(); conn.close()
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════════════════
# METAS PUEAA/PSMV
# ═══════════════════════════════════════════════════════════════════════

@proy2_bp.route("/api/<int:pid>/metas", methods=["POST"])
@login_requerido
def api_meta(pid):
    data = request.get_json() or {}
    if not data.get("meta"):
        return jsonify({"ok": False, "error": "Meta requerida"}), 400
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO metas_proyecto
        (proyecto_id, anio, semestre, meta, cumplida, observaciones)
        VALUES (?,?,?,?,?,?)
    """, (pid, data.get("anio", datetime.now().year),
          data.get("semestre"), data["meta"],
          int(data.get("cumplida",0)), data.get("observaciones","")))
    conn.commit(); conn.close()
    return jsonify({"ok": True, "id": cur.lastrowid}), 201


@proy2_bp.route("/api/metas/<int:mid>", methods=["PUT"])
@login_requerido
def api_actualizar_meta(mid):
    data = request.get_json() or {}
    conn = get_db()
    conn.execute(
        "UPDATE metas_proyecto SET cumplida=?,observaciones=? WHERE id=?",
        (int(data.get("cumplida",0)), data.get("observaciones",""), mid)
    )
    conn.commit(); conn.close()
    return jsonify({"ok": True})


@proy2_bp.route("/api/metas/<int:mid>", methods=["DELETE"])
@login_requerido
def api_eliminar_meta(mid):
    conn = get_db()
    conn.execute("DELETE FROM metas_proyecto WHERE id=?", (mid,))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════════════════
# PROGRAMA_5: DOCUMENTOS ↔ PROYECTOS
# ═══════════════════════════════════════════════════════════════════════

@proy2_bp.route("/api/<int:pid>/documentos", methods=["GET"])
@login_requerido
def api_docs_proyecto(pid):
    """Lista documentos asociados al proyecto."""
    conn = get_db()
    rows = conn.execute("""
        SELECT dp.id as rel_id, dp.tipo_relacion, dp.observaciones,
               r.pk_registro_id as id, r.codigo_completo as codigo,
               r.asunto_resumen as asunto, r.fecha_radicacion as fecha,
               r.estado, r.area, r.tipo_documento
        FROM documentos_proyecto dp
        JOIN registro_central r ON dp.documento_id=r.pk_registro_id
        WHERE dp.proyecto_id=?
        ORDER BY r.fecha_radicacion DESC
    """, (pid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@proy2_bp.route("/api/<int:pid>/documentos", methods=["POST"])
@login_requerido
def api_asociar_doc(pid):
    """Asocia un documento existente al proyecto."""
    data = request.get_json() or {}
    doc_id = data.get("documento_id")
    if not doc_id:
        return jsonify({"ok": False, "error": "documento_id requerido"}), 400
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO documentos_proyecto
            (documento_id, proyecto_id, tipo_relacion, observaciones)
            VALUES (?,?,?,?)
        """, (doc_id, pid, data.get("tipo_relacion","soporte"),
              data.get("observaciones","")))
        conn.commit()
        log_action(accion="ASSOCIATE_DOC", modulo="proyectos",
                   descripcion=f"Documento {doc_id} asociado a proyecto {pid}")
        conn.close()
        return jsonify({"ok": True}), 201
    except Exception as e:
        conn.rollback(); conn.close()
        if "UNIQUE" in str(e):
            return jsonify({"ok": False, "error": "Ya está asociado"}), 409
        return jsonify({"ok": False, "error": str(e)}), 500


@proy2_bp.route("/api/<int:pid>/documentos/<int:doc_id>", methods=["DELETE"])
@login_requerido
def api_desasociar_doc(pid, doc_id):
    """Quita la asociación de un documento al proyecto."""
    conn = get_db()
    conn.execute(
        "DELETE FROM documentos_proyecto WHERE documento_id=? AND proyecto_id=?",
        (doc_id, pid)
    )
    conn.commit(); conn.close()
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════════════════
# PROGRAMA_5: DOCUMENTOS SOPORTE DE METAS
# ═══════════════════════════════════════════════════════════════════════

@proy2_bp.route("/api/metas/<int:mid>/documentos", methods=["GET"])
@login_requerido
def api_docs_meta(mid):
    conn = get_db()
    rows = conn.execute("""
        SELECT md.id as rel_id,
               r.pk_registro_id as id, r.codigo_completo as codigo,
               r.asunto_resumen as asunto, r.fecha_radicacion as fecha
        FROM meta_documentos md
        JOIN registro_central r ON md.documento_id=r.pk_registro_id
        WHERE md.meta_id=?
        ORDER BY r.fecha_radicacion DESC
    """, (mid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@proy2_bp.route("/api/metas/<int:mid>/documentos", methods=["POST"])
@login_requerido
def api_asociar_doc_meta(mid):
    data   = request.get_json() or {}
    doc_id = data.get("documento_id")
    if not doc_id:
        return jsonify({"ok": False, "error": "documento_id requerido"}), 400
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO meta_documentos (meta_id, documento_id) VALUES (?,?)",
            (mid, doc_id)
        )
        conn.commit(); conn.close()
        return jsonify({"ok": True}), 201
    except Exception as e:
        conn.rollback(); conn.close()
        if "UNIQUE" in str(e):
            return jsonify({"ok": False, "error": "Ya existe"}), 409
        return jsonify({"ok": False, "error": str(e)}), 500


@proy2_bp.route("/api/metas/<int:mid>/documentos/<int:doc_id>", methods=["DELETE"])
@login_requerido
def api_desasociar_doc_meta(mid, doc_id):
    conn = get_db()
    conn.execute("DELETE FROM meta_documentos WHERE meta_id=? AND documento_id=?",
                 (mid, doc_id))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════════════════
# PROGRAMA_5: INFORME DE AVANCE EXCEL
# ═══════════════════════════════════════════════════════════════════════

@proy2_bp.route("/api/<int:pid>/informe_avance")
@login_requerido
def api_informe_avance(pid):
    """
    Genera Excel con 3 hojas:
      1. Resumen del proyecto
      2. Metas PUEAA/PSMV con documentos soporte
      3. Documentos asociados
    """
    import pandas as pd
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    conn = get_db()
    proy = conn.execute("""
        SELECT p.pk_proyecto_id as id, p.codigo, p.nombre, p.descripcion,
               p.tipo_proyecto, p.estado,
               p.presupuesto as presupuesto_total,
               p.valor_ejecutado as costo_real,
               COALESCE(p.ingresos_totales,0) as ingresos_totales,
               p.porcentaje_completado as porcentaje_avance,
               p.fecha_inicio as fecha_inicio_plan,
               p.fecha_limite as fecha_fin_plan,
               p.objetivo,
               (SELECT nombre_completo FROM usuarios
                WHERE pk_usuario_id=p.responsable_id) as responsable_nombre
        FROM proyectos p WHERE p.pk_proyecto_id=?
    """, (pid,)).fetchone()

    if not proy:
        conn.close()
        return jsonify({"error": "Proyecto no encontrado"}), 404

    metas = conn.execute(
        "SELECT * FROM metas_proyecto WHERE proyecto_id=? ORDER BY anio,semestre",
        (pid,)
    ).fetchall()

    lista_metas = []
    for m in metas:
        docs_meta = conn.execute("""
            SELECT r.codigo_completo, r.asunto_resumen, r.fecha_radicacion
            FROM meta_documentos md
            JOIN registro_central r ON md.documento_id=r.pk_registro_id
            WHERE md.meta_id=?
        """, (m["id"],)).fetchall()
        lista_metas.append({
            "Año":      m["anio"],
            "Período":  f"S{m['semestre']}" if m["semestre"] else "Anual",
            "Meta":     m["meta"],
            "Cumplida": "Sí" if m["cumplida"] else "No",
            "Observaciones": m["observaciones"] or "",
            "Documentos soporte": " | ".join(
                f"{d['codigo_completo']} — {d['asunto_resumen'][:40]}"
                for d in docs_meta
            )
        })

    docs_proy = conn.execute("""
        SELECT r.codigo_completo as Código, r.asunto_resumen as Asunto,
               r.fecha_radicacion as Fecha, r.estado as Estado,
               dp.tipo_relacion as Relación
        FROM documentos_proyecto dp
        JOIN registro_central r ON dp.documento_id=r.pk_registro_id
        WHERE dp.proyecto_id=?
        ORDER BY r.fecha_radicacion DESC
    """, (pid,)).fetchall()

    tareas = conn.execute("""
        SELECT nombre as Tarea, estado as Estado,
               COALESCE(porcentaje_avance,0) || '%' as Avance,
               prioridad as Prioridad,
               fecha_inicio_plan as "Inicio plan",
               fecha_fin_plan as "Fin plan",
               COALESCE(costo_estimado,0) as "Costo estimado",
               COALESCE(costo_real,0) as "Costo real"
        FROM tareas_proyecto WHERE proyecto_id=?
        ORDER BY orden,id
    """, (pid,)).fetchall()
    conn.close()

    # ── Construir Excel ───────────────────────────────────────────────
    output = BytesIO()
    C_AZUL  = "1E3A8A"
    C_BLANCO = "FFFFFF"
    C_GRIS   = "F1F5F9"

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        # Hoja 1: Resumen
        p = dict(proy)
        saldo = float(p["ingresos_totales"]) - float(p["costo_real"] or 0)
        resumen_data = {
            "Campo": ["Código","Nombre","Tipo","Estado","Responsable",
                      "Avance (%)","Presupuesto","Costo real",
                      "Ingresos totales","Saldo",
                      "Fecha inicio","Fecha límite","Objetivo",
                      "Fecha informe"],
            "Valor":  [p["codigo"], p["nombre"], p["tipo_proyecto"],
                       p["estado"], p.get("responsable_nombre","—"),
                       p["porcentaje_avance"],
                       f"${float(p['presupuesto_total']):,.0f}",
                       f"${float(p['costo_real'] or 0):,.0f}",
                       f"${float(p['ingresos_totales']):,.0f}",
                       f"${saldo:,.0f}",
                       p["fecha_inicio_plan"] or "—",
                       p["fecha_fin_plan"] or "—",
                       p.get("objetivo","—"),
                       datetime.now().strftime("%d/%m/%Y %H:%M")]
        }
        df_res = pd.DataFrame(resumen_data)
        df_res.to_excel(writer, sheet_name="Resumen", index=False)

        # Hoja 2: Metas
        if lista_metas:
            pd.DataFrame(lista_metas).to_excel(
                writer, sheet_name="Metas PUEAA-PSMV", index=False)

        # Hoja 3: Tareas
        if tareas:
            pd.DataFrame([dict(t) for t in tareas]).to_excel(
                writer, sheet_name="Tareas", index=False)

        # Hoja 4: Documentos asociados
        if docs_proy:
            pd.DataFrame([dict(d) for d in docs_proy]).to_excel(
                writer, sheet_name="Documentos", index=False)

        # Formato cabeceras
        azul_fill = PatternFill("solid", fgColor=C_AZUL)
        for ws in writer.book.worksheets:
            for cell in ws[1]:
                cell.font      = Font(bold=True, color=C_BLANCO, name="Calibri")
                cell.fill      = azul_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
            for col in ws.columns:
                ml = max(len(str(c.value or "")) for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(ml + 4, 60)

    output.seek(0)
    fname = (f"InformeAvance_{proy['codigo']}_"
             f"{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx")
    return send_file(output, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ═══════════════════════════════════════════════════════════════════════
# PROGRAMA_5: BÚSQUEDA DE DOCUMENTOS (para asociar desde proyectos)
# ═══════════════════════════════════════════════════════════════════════

@proy2_bp.route("/api/buscar_documento")
@login_requerido
def api_buscar_documento():
    """Busca documentos por código o asunto para asociarlos a proyectos/metas."""
    q   = request.args.get("q","").strip()
    pid = request.args.get("excluir_proyecto", type=int)
    if len(q) < 2:
        return jsonify([])
    conn = get_db()
    sql = """
        SELECT r.pk_registro_id as id, r.codigo_completo as codigo,
               r.asunto_resumen as asunto, r.fecha_radicacion as fecha,
               r.estado
        FROM registro_central r
        WHERE (r.codigo_completo LIKE ? OR r.asunto_resumen LIKE ?)
    """
    params = [f"%{q}%", f"%{q}%"]
    if pid:
        sql += """ AND r.pk_registro_id NOT IN (
            SELECT documento_id FROM documentos_proyecto WHERE proyecto_id=?
        )"""
        params.append(pid)
    sql += " ORDER BY r.fecha_radicacion DESC LIMIT 15"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
