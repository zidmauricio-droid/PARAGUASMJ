"""
routes/suscriptores.py — GC-01 Gestión Comercial: Suscriptores.
"""
import logging
from flask import Blueprint, render_template, request, jsonify, session
from core.database_manager import get_db
from core.seguridad import login_requerido, rol_requerido
from core.auditoria import auditar

sus_bp = Blueprint("suscriptores", __name__, url_prefix="/suscriptores")
_log = logging.getLogger("sigca.suscriptores")


@sus_bp.route("/")
@login_requerido
def panel():
    return render_template("suscriptores/panel.html")


@sus_bp.route("/api/suscriptores")
@login_requerido
def api_listar():
    estado = request.args.get("estado", "")
    zona   = request.args.get("zona", "")
    q      = request.args.get("q", "")
    conn   = get_db()
    try:
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "gc_suscriptores" not in tablas:
            return jsonify({"ok": False, "error": "Módulo no inicializado"})

        sql = """
            SELECT s.*, c.nombre_completo as nombre, c.telefono, c.email
            FROM gc_suscriptores s
            LEFT JOIN contactos c ON c.pk_contacto_id = s.fk_contacto_id
            WHERE 1=1
        """
        params = []
        if estado:
            sql += " AND s.estado=?"; params.append(estado)
        if zona:
            sql += " AND s.fk_zona_id=?"; params.append(int(zona))
        if q:
            sql += " AND (s.codigo_suscriptor LIKE ? OR c.nombre_completo LIKE ? OR s.numero_medidor LIKE ?)"
            p = f"%{q}%"
            params += [p, p, p]
        sql += " ORDER BY s.codigo_suscriptor"
        rows = conn.execute(sql, params).fetchall()

        totales = conn.execute("""
            SELECT estado, COUNT(*) as cnt FROM gc_suscriptores GROUP BY estado
        """).fetchall()
        resumen = {r["estado"]: r["cnt"] for r in totales}
        return jsonify({"ok": True, "suscriptores": [dict(r) for r in rows],
                        "resumen": resumen, "total": len(rows)})
    finally:
        conn.close()


@sus_bp.route("/api/suscriptores", methods=["POST"])
@login_requerido
def api_crear():
    d = request.get_json(silent=True) or {}
    if not d.get("codigo_suscriptor"):
        return jsonify({"ok": False, "error": "codigo_suscriptor requerido"})
    conn = get_db()
    try:
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "gc_suscriptores" not in tablas:
            return jsonify({"ok": False, "error": "Módulo no inicializado"})
        cur = conn.execute("""
            INSERT INTO gc_suscriptores
            (fk_contacto_id, codigo_suscriptor, numero_medidor, fecha_conexion,
             tipo_suscriptor, estado, estrato, aforo_m3, fk_zona_id,
             coordenada_lat, coordenada_lon, observaciones)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            d.get("fk_contacto_id"),
            str(d["codigo_suscriptor"]).strip(),
            d.get("numero_medidor", ""),
            d.get("fecha_conexion", ""),
            d.get("tipo_suscriptor", "RESIDENCIAL"),
            d.get("estado", "ACTIVO"),
            int(d.get("estrato", 1)),
            float(d.get("aforo_m3", 0)),
            d.get("fk_zona_id"),
            d.get("coordenada_lat"),
            d.get("coordenada_lon"),
            d.get("observaciones", ""),
        ))
        conn.commit()
        auditar("SUS_NUEVO",
                detalle=f"Suscriptor {d['codigo_suscriptor']} creado",
                modulo="suscriptores")
        return jsonify({"ok": True, "pk_suscriptor_id": cur.lastrowid})
    except Exception as e:
        conn.rollback()
        _log.error("api_crear: %s", e, exc_info=True)
        if "UNIQUE" in str(e):
            return jsonify({"ok": False, "error": "El código ya existe"})
        return jsonify({"ok": False, "error": "Error interno"})
    finally:
        conn.close()


@sus_bp.route("/api/suscriptores/<int:sid>", methods=["PUT"])
@login_requerido
def api_actualizar(sid):
    d = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        campos_permitidos = {
            "numero_medidor", "tipo_suscriptor", "estado", "estrato",
            "aforo_m3", "fk_zona_id", "coordenada_lat", "coordenada_lon",
            "observaciones", "saldo_cartera"
        }
        sets, params = [], []
        for k, v in d.items():
            if k in campos_permitidos:
                sets.append(f"{k}=?")
                params.append(v)
        if not sets:
            return jsonify({"ok": False, "error": "Sin campos a actualizar"})
        params.append(sid)
        conn.execute(f"UPDATE gc_suscriptores SET {','.join(sets)} WHERE pk_suscriptor_id=?",
                     params)
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@sus_bp.route("/api/suscriptores/<int:sid>")
@login_requerido
def api_detalle(sid):
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT s.*, c.nombre_completo, c.telefono, c.email, c.direccion,
                   z.nombre as zona_nombre
            FROM gc_suscriptores s
            LEFT JOIN contactos c ON c.pk_contacto_id = s.fk_contacto_id
            LEFT JOIN zonas_prestacion z ON z.pk_zona_id = s.fk_zona_id
            WHERE s.pk_suscriptor_id=?
        """, (sid,)).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "No encontrado"})
        # Conexiones recientes
        conexiones = conn.execute("""
            SELECT * FROM gc_conexiones WHERE fk_suscriptor_id=?
            ORDER BY fecha_solicitud DESC LIMIT 10
        """, (sid,)).fetchall()
        return jsonify({"ok": True, "suscriptor": dict(row),
                        "conexiones": [dict(c) for c in conexiones]})
    finally:
        conn.close()


@sus_bp.route("/api/conexiones", methods=["POST"])
@login_requerido
def api_conexion():
    d = request.get_json(silent=True) or {}
    required = ("fk_suscriptor_id", "tipo", "fecha_solicitud")
    for f in required:
        if not d.get(f):
            return jsonify({"ok": False, "error": f"Campo requerido: {f}"})
    conn = get_db()
    try:
        cur = conn.execute("""
            INSERT INTO gc_conexiones
            (fk_suscriptor_id, tipo, fecha_solicitud, estado, valor_cobrado,
             tecnico_asignado, observaciones, usuario)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            int(d["fk_suscriptor_id"]),
            str(d["tipo"]).upper(),
            str(d["fecha_solicitud"])[:10],
            d.get("estado", "PENDIENTE"),
            float(d.get("valor_cobrado", 0)),
            d.get("tecnico_asignado", ""),
            d.get("observaciones", ""),
            session.get("nombre_usuario", "anonimo"),
        ))
        conn.commit()
        return jsonify({"ok": True, "pk_conexion_id": cur.lastrowid})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)})
    finally:
        conn.close()


@sus_bp.route("/api/causales")
@login_requerido
def api_causales():
    """Causales PQRS parametrizables — Nivel 3 RC6."""
    servicio = request.args.get("servicio", "").upper()
    conn = get_db()
    try:
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "gc_pqrs_causales" not in tablas:
            return jsonify({"ok": False, "causales": []})
        q = "SELECT * FROM gc_pqrs_causales WHERE activo=1"
        params = []
        if servicio in ("ACUEDUCTO", "ALCANTARILLADO"):
            q += " AND (servicio=? OR servicio='AMBOS')"
            params.append(servicio)
        q += " ORDER BY orden, codigo"
        rows = conn.execute(q, params).fetchall()
        return jsonify({"ok": True, "causales": [dict(r) for r in rows]})
    finally:
        conn.close()


@sus_bp.route("/api/causales", methods=["POST"])
@login_requerido
@rol_requerido("admin")
def api_causal_crear():
    """Crear causal parametrizable."""
    d = request.get_json(silent=True) or {}
    if not d.get("nombre"):
        return jsonify({"ok": False, "error": "nombre requerido"})
    conn = get_db()
    try:
        # Auto-generar código
        ultimo = conn.execute(
            "SELECT MAX(CAST(SUBSTR(codigo,3) AS INTEGER)) as m FROM gc_pqrs_causales WHERE codigo LIKE 'C-%'"
        ).fetchone()["m"] or 0
        codigo = f"C-{str(ultimo + 1).zfill(3)}"
        conn.execute(
            "INSERT INTO gc_pqrs_causales (codigo,nombre,servicio,sla_dias,orden) VALUES (?,?,?,?,?)",
            (codigo, d["nombre"], d.get("servicio", "AMBOS"),
             int(d.get("sla_dias", 15)), int(d.get("orden", 0)))
        )
        conn.commit()
        return jsonify({"ok": True, "codigo": codigo})
    finally:
        conn.close()


@sus_bp.route("/api/causales/<int:cid>", methods=["PUT"])
@login_requerido
@rol_requerido("admin")
def api_causal_editar(cid):
    d = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        conn.execute("""
            UPDATE gc_pqrs_causales
            SET nombre=?, servicio=?, sla_dias=?, activo=?, orden=?
            WHERE pk_causal_id=?
        """, (d.get("nombre"), d.get("servicio", "AMBOS"),
              int(d.get("sla_dias", 15)), 1 if d.get("activo", True) else 0,
              int(d.get("orden", 0)), cid))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()
