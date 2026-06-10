"""
routes/emergencias.py — PEC 2026 SIGCA
Fórmula exacta del PEC:
  V = (imp_alcance×0.10 + imp_tiempo×0.80 + imp_costo×0.00 + imp_calidad×0.10) × probabilidad
  Alta ≥ 0.50 | Media ≥ 0.25 | Baja < 0.25
Genera: Listado de riesgos (Excel), Documento PEC (Word/PDF).
"""
from flask import (Blueprint, render_template, request, jsonify,
                   session, send_file)
from core.database_manager import get_db
from core.seguridad import login_requerido, rol_requerido
from utils.audit import log_action
from datetime import datetime
from io import BytesIO

em_bp = Blueprint("emergencias", __name__, url_prefix="/emergencias")

# ── Constantes PEC 2026 ───────────────────────────────────────────
POND = {"alcance": 0.10, "tiempo": 0.80, "costo": 0.00, "calidad": 0.10}
UMBR = {"alta": 0.50, "media": 0.25}

COLORES_ALERTA = {
    "verde":    {"hex": "#10b981", "class": "verde",    "icon": "🟢"},
    "amarillo": {"hex": "#f59e0b", "class": "amarillo", "icon": "🟡"},
    "naranja":  {"hex": "#f97316", "class": "naranja",  "icon": "🟠"},
    "rojo":     {"hex": "#ef4444", "class": "rojo",     "icon": "🔴"},
}

PROTOCOLO_ALERTA = {
    "verde": {
        "disminucion": "< 10% del caudal normal",
        "suspension":  "Sin suspensión",
        "responsable": "Operador de redes en bitácora preventiva",
        "acciones":    "Monitoreo diario, registro caudal/turbiedad, inspección visual bocatoma y redes.",
    },
    "amarillo": {
        "disminucion": "Hasta el 25% / Suspensión ≤ 8 horas",
        "suspension":  "≤ 8 horas",
        "responsable": "Operador y Jefe Operativo",
        "acciones":    "Monitoreo permanente, limpieza estructura de captación, ajustes operativos PTAP, registro técnico.",
    },
    "naranja": {
        "disminucion": "Del 26% al 50% / Suspensión 9-24 horas",
        "suspension":  "9-24 horas",
        "responsable": "Representante Legal y Comité PEC",
        "acciones":    "Activación Comité PEC, racionamientos sectorizados, comunicado oficial a comunidad, evaluación EDAN, preparación carrotanques.",
    },
    "rojo": {
        "disminucion": "Del 51% al 100% / Suspensión > 24 horas",
        "suspension":  "> 24 horas",
        "responsable": "Comité PEC en pleno y Enlace CMGRD",
        "acciones":    "Activación total PEC, suministro por carrotanques, notificación oficial CMGRD Villeta y SSPD, suspensión preventiva si condiciones sanitarias inseguras.",
    },
}


# ══════════════════════════════════════════════════════════════════
# FÓRMULA EXACTA DEL PEC
# ══════════════════════════════════════════════════════════════════
def calcular_valoracion_pec(prob: float, ia: float, it: float,
                             ic: float, iq: float) -> tuple:
    """
    Valoración global según PEC 2026 SIGCA.
    V = (ia×0.10 + it×0.80 + ic×0.00 + iq×0.10) × probabilidad
    """
    if prob is None: prob = 0
    suma = (float(ia or 0)*POND["alcance"] +
            float(it or 0)*POND["tiempo"]  +
            float(ic or 0)*POND["costo"]   +
            float(iq or 0)*POND["calidad"])
    v = round(suma * float(prob), 4)
    if v >= UMBR["alta"]:   return v, "Alta",  "rojo"
    if v >= UMBR["media"]:  return v, "Media", "amarillo"
    return v, "Baja", "verde"


def nivel_alerta_quebrada(nivel_cm: float) -> str:
    if nivel_cm < 100:  return "verde"
    if nivel_cm < 130:  return "amarillo"
    if nivel_cm < 200:  return "naranja"
    return "rojo"


# ══════════════════════════════════════════════════════════════════
# PANEL HTML
# ══════════════════════════════════════════════════════════════════
@em_bp.route("/")
@login_requerido
def panel():
    return render_template("emergencias/panel.html")


# ══════════════════════════════════════════════════════════════════
# MONITOREO DE QUEBRADA
# ══════════════════════════════════════════════════════════════════
@em_bp.route("/api/niveles", methods=["GET"])
@login_requerido
def api_niveles():
    n     = request.args.get("n", 30, type=int)
    sitio = request.args.get("sitio", "")
    conn  = get_db()
    sql   = "SELECT * FROM niveles_quebrada WHERE 1=1"
    p     = []
    if sitio: sql += " AND punto_medicion=?"; p.append(sitio)
    sql  += f" ORDER BY fecha DESC LIMIT {min(n,500)}"
    rows  = conn.execute(sql, p).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@em_bp.route("/api/niveles", methods=["POST"])
@login_requerido
def api_registrar_nivel():
    data     = request.get_json() or {}
    nivel_cm = float(data.get("nivel_cm", 0))
    if nivel_cm < 0:
        return jsonify({"ok": False, "error": "Nivel inválido"}), 400
    alerta = nivel_alerta_quebrada(nivel_cm)
    conn   = get_db()
    cur = conn.execute("""
        INSERT INTO niveles_quebrada
        (punto_medicion, nivel_cm, nivel_alerta, horas_servicio_aplicadas,
         observaciones, registrado_por, fecha)
        VALUES (?,?,?,?,?,?,?)
    """, (data.get("punto_medicion","Sitio 1"), nivel_cm, alerta,
          data.get("horas_servicio_aplicadas"),
          data.get("observaciones",""), session.get("usuario_id"),
          datetime.now().isoformat()))
    conn.commit()
    protocolo = PROTOCOLO_ALERTA.get(alerta, {})
    conn.close()
    log_action(accion="REGISTRO_NIVEL", modulo="emergencias",
               descripcion=f"Nivel quebrada {nivel_cm}cm → {alerta.upper()}")
    return jsonify({"ok": True, "id": cur.lastrowid,
                    "nivel_alerta": alerta, "protocolo": protocolo}), 201


@em_bp.route("/api/alertas_config")
@login_requerido
def api_alertas_config():
    conn = get_db()
    rows = conn.execute("SELECT * FROM config_alertas ORDER BY nivel_min_cm").fetchall()
    conn.close()
    result = [dict(r) for r in rows]
    # Inyectar protocolo detallado del PEC
    for item in result:
        item["protocolo"] = PROTOCOLO_ALERTA.get(item["nivel"], {})
    return jsonify(result)


@em_bp.route("/api/alertas_config/<int:aid>", methods=["PUT"])
@login_requerido
@rol_requerido("admin")
def api_actualizar_alerta(aid):
    data = request.get_json() or {}
    conn = get_db()
    conn.execute("""
        UPDATE config_alertas SET
            horas_servicio_max=COALESCE(?,horas_servicio_max),
            acciones_resumen=COALESCE(?,acciones_resumen),
            comunicacion=COALESCE(?,comunicacion),
            activacion_institucional=COALESCE(?,activacion_institucional),
            actualizado_en=?
        WHERE id=?
    """, (data.get("horas_servicio_max"), data.get("acciones_resumen"),
          data.get("comunicacion"), data.get("activacion_institucional"),
          datetime.now().isoformat(), aid))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════
# MATRIZ DE RIESGOS PEC (fórmula exacta)
# ══════════════════════════════════════════════════════════════════
@em_bp.route("/api/riesgos", methods=["GET"])
@login_requerido
def api_listar_riesgos():
    pid  = request.args.get("proyecto_id", type=int)
    conn = get_db()
    sql  = """
        SELECT r.*,
               u.nombre_completo as responsable_nombre
        FROM riesgos_pec r
        LEFT JOIN usuarios u ON r.responsable_id=u.pk_usuario_id
        WHERE 1=1
    """
    p = []
    if pid: sql += " AND r.proyecto_id=?"; p.append(pid)
    sql += " ORDER BY r.valoracion_global DESC, r.codigo"
    rows = conn.execute(sql, p).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@em_bp.route("/api/riesgos", methods=["POST"])
@login_requerido
def api_crear_riesgo():
    data = request.get_json() or {}
    if not data.get("nombre"):
        return jsonify({"ok": False, "error": "Nombre requerido"}), 400
    conn = get_db()
    pid  = data.get("proyecto_id")
    n    = conn.execute("SELECT COUNT(*) as c FROM riesgos_pec WHERE proyecto_id=?",
                        (pid,)).fetchone()["c"]
    codigo = data.get("codigo") or f"R-{n+1:02d}"
    val, prioridad, color = calcular_valoracion_pec(
        data.get("probabilidad", 0),
        data.get("impacto_alcance", 0),
        data.get("impacto_tiempo", 0),
        data.get("impacto_costo", 0),
        data.get("impacto_calidad", 0)
    )
    cur = conn.execute("""
        INSERT INTO riesgos_pec (
            proyecto_id, codigo, nombre, tipo, categoria,
            afecta_alcance, afecta_tiempo, afecta_costo, afecta_calidad,
            impacto_directo, impacto_indirecto,
            probabilidad, impacto_alcance, impacto_tiempo, impacto_costo, impacto_calidad,
            ponderacion_alcance, ponderacion_tiempo, ponderacion_costo, ponderacion_calidad,
            valoracion_global, prioridad, color_semaforo,
            dueno, plan_respuesta, activado, estado,
            justificacion_evidencia, justificacion_tecnica, justificacion_juicio_experto,
            identificado_por, fecha_identificacion
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0.10,0.80,0.00,0.10,?,?,?,?,?,?,?,?,?,?,?,date('now'))
    """, (pid, codigo, data["nombre"], data.get("tipo","amenaza"), data.get("categoria",""),
          int(data.get("afecta_alcance",0)), int(data.get("afecta_tiempo",1)),
          int(data.get("afecta_costo",0)),   int(data.get("afecta_calidad",0)),
          int(data.get("impacto_directo",1)), int(data.get("impacto_indirecto",0)),
          float(data.get("probabilidad",0)),
          float(data.get("impacto_alcance",0)), float(data.get("impacto_tiempo",0)),
          float(data.get("impacto_costo",0)),   float(data.get("impacto_calidad",0)),
          val, prioridad, color,
          data.get("dueno",""), data.get("plan_respuesta",""),
          int(data.get("activado",0)), data.get("estado","identificado"),
          data.get("justificacion_evidencia",""),
          data.get("justificacion_tecnica",""),
          data.get("justificacion_juicio_experto",""),
          session.get("usuario_id")))
    conn.commit()
    rid = cur.lastrowid
    log_action(accion="CREATE_RIESGO", modulo="emergencias",
               descripcion=f"{codigo} — {prioridad} (V={val})")
    conn.close()
    return jsonify({"ok": True, "id": rid, "codigo": codigo,
                    "valoracion_global": val, "prioridad": prioridad}), 201


@em_bp.route("/api/riesgos/<int:rid>", methods=["PUT"])
@login_requerido
def api_actualizar_riesgo(rid):
    data  = request.get_json() or {}
    conn  = get_db()
    viejo = conn.execute("SELECT * FROM riesgos_pec WHERE id=?", (rid,)).fetchone()
    if not viejo: conn.close(); return jsonify({"ok": False}), 404

    merged = dict(viejo)
    merged.update({k: v for k, v in data.items() if v is not None})
    val, prioridad, color = calcular_valoracion_pec(
        merged.get("probabilidad",0), merged.get("impacto_alcance",0),
        merged.get("impacto_tiempo",0), merged.get("impacto_costo",0),
        merged.get("impacto_calidad",0)
    )
    # Guardar historial
    conn.execute("""
        INSERT INTO historial_riesgos
        (riesgo_id,probabilidad_anterior,probabilidad_nueva,
         valoracion_anterior,valoracion_nueva,
         prioridad_anterior,prioridad_nueva,comentario,modificado_por)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, (rid, viejo["probabilidad"], data.get("probabilidad",viejo["probabilidad"]),
          viejo["valoracion_global"], val,
          viejo["prioridad"], prioridad,
          data.get("comentario",""), session.get("usuario_id")))
    conn.execute("""
        UPDATE riesgos_pec SET
            nombre=COALESCE(?,nombre), descripcion=COALESCE(?,descripcion),
            probabilidad=COALESCE(?,probabilidad),
            impacto_alcance=COALESCE(?,impacto_alcance),
            impacto_tiempo=COALESCE(?,impacto_tiempo),
            impacto_costo=COALESCE(?,impacto_costo),
            impacto_calidad=COALESCE(?,impacto_calidad),
            valoracion_global=?, prioridad=?, color_semaforo=?,
            dueno=COALESCE(?,dueno), plan_respuesta=COALESCE(?,plan_respuesta),
            activado=COALESCE(?,activado), estado=COALESCE(?,estado),
            justificacion_evidencia=COALESCE(?,justificacion_evidencia),
            justificacion_tecnica=COALESCE(?,justificacion_tecnica),
            actualizado_por=?, actualizado_en=?
        WHERE id=?
    """, (data.get("nombre"), data.get("descripcion"),
          data.get("probabilidad"), data.get("impacto_alcance"),
          data.get("impacto_tiempo"), data.get("impacto_costo"),
          data.get("impacto_calidad"),
          val, prioridad, color,
          data.get("dueno"), data.get("plan_respuesta"),
          data.get("activado"), data.get("estado"),
          data.get("justificacion_evidencia"), data.get("justificacion_tecnica"),
          session.get("usuario_id"), datetime.now().isoformat(), rid))
    conn.commit(); conn.close()
    return jsonify({"ok": True, "valoracion_global": val, "prioridad": prioridad})


@em_bp.route("/api/riesgos/<int:rid>/activar", methods=["POST"])
@login_requerido
def api_activar_riesgo(rid):
    conn = get_db()
    conn.execute("""UPDATE riesgos_pec SET activado=1,fecha_activacion=?,
                    estado='ocurrido',actualizado_en=? WHERE id=?""",
                 (datetime.now().date().isoformat(), datetime.now().isoformat(), rid))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


@em_bp.route("/api/riesgos/<int:rid>/historial")
@login_requerido
def api_historial_riesgo(rid):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM historial_riesgos WHERE riesgo_id=? ORDER BY fecha DESC", (rid,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ══════════════════════════════════════════════════════════════════
# INVENTARIO DE RECURSOS
# ══════════════════════════════════════════════════════════════════
@em_bp.route("/api/recursos")
@login_requerido
def api_recursos():
    cat  = request.args.get("categoria","")
    conn = get_db()
    sql  = "SELECT * FROM recursos_emergencia WHERE 1=1"
    p    = []
    if cat: sql += " AND categoria=?"; p.append(cat)
    rows = conn.execute(sql + " ORDER BY categoria, nombre", p).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@em_bp.route("/api/recursos", methods=["POST"])
@login_requerido
def api_crear_recurso():
    data = request.get_json() or {}
    conn = get_db()
    cur  = conn.execute("""
        INSERT INTO recursos_emergencia
        (categoria,nombre,descripcion,cantidad,ubicacion,estado,proveedor,observaciones)
        VALUES(?,?,?,?,?,?,?,?)
    """, (data.get("categoria","General"), data.get("nombre",""),
          data.get("descripcion",""), int(data.get("cantidad",1)),
          data.get("ubicacion",""), data.get("estado","disponible"),
          data.get("proveedor",""), data.get("observaciones","")))
    conn.commit(); conn.close()
    return jsonify({"ok": True, "id": cur.lastrowid}), 201


@em_bp.route("/api/recursos/<int:rid>", methods=["PUT"])
@login_requerido
def api_actualizar_recurso(rid):
    data = request.get_json() or {}
    conn = get_db()
    conn.execute("""UPDATE recursos_emergencia
        SET estado=COALESCE(?,estado), cantidad=COALESCE(?,cantidad),
            observaciones=COALESCE(?,observaciones),
            fecha_ultimo_mantenimiento=COALESCE(?,fecha_ultimo_mantenimiento)
        WHERE id=?""",
        (data.get("estado"), data.get("cantidad"), data.get("observaciones"),
         data.get("fecha_ultimo_mantenimiento"), rid))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════
# EVENTOS Y EDAN
# ══════════════════════════════════════════════════════════════════
@em_bp.route("/api/eventos", methods=["GET"])
@login_requerido
def api_eventos():
    conn = get_db()
    rows = conn.execute("""
        SELECT e.*,
               (SELECT COUNT(*) FROM evaluacion_danos
                WHERE evento_emergencia_id=e.id) as n_danos
        FROM eventos_emergencia e ORDER BY e.fecha_inicio DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@em_bp.route("/api/eventos", methods=["POST"])
@login_requerido
def api_crear_evento():
    data = request.get_json() or {}
    conn = get_db()
    cur  = conn.execute("""
        INSERT INTO eventos_emergencia
        (tipo,nivel_alerta,fecha_inicio,causa,componentes_afectados,
         numero_suscriptores_afectados,horas_suspension_servicio,
         acciones_realizadas,costo_estimado,creado_por)
        VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (data.get("tipo","otro"), data.get("nivel_alerta","verde"),
          datetime.now().isoformat(), data.get("causa",""),
          data.get("componentes_afectados",""),
          data.get("numero_suscriptores_afectados"),
          data.get("horas_suspension_servicio"),
          data.get("acciones_realizadas",""),
          data.get("costo_estimado"), session.get("usuario_id")))
    conn.commit(); conn.close()
    return jsonify({"ok": True, "id": cur.lastrowid}), 201


@em_bp.route("/api/eventos/<int:eid>/cerrar", methods=["POST"])
@login_requerido
def api_cerrar_evento(eid):
    data = request.get_json() or {}
    conn = get_db()
    conn.execute("""UPDATE eventos_emergencia
        SET fecha_fin=?,lecciones_aprendidas=?,costo_real=?,requiere_actualizacion_pec=?
        WHERE id=?""",
        (datetime.now().isoformat(), data.get("lecciones",""),
         data.get("costo_real"), int(data.get("requiere_actualizacion_pec",0)), eid))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


@em_bp.route("/api/eventos/<int:eid>/edan", methods=["POST"])
@login_requerido
def api_registrar_edan(eid):
    data = request.get_json() or {}
    conn = get_db()
    cur  = conn.execute("""
        INSERT INTO evaluacion_danos
        (evento_emergencia_id,componente,descripcion_dano,requiere_cierre_flujo,
         impacto_servicio,numero_suscriptores_afectados,recursos_requeridos,
         tiempo_estimado_reparacion_horas,fotos,evaluador_id,fecha_evaluacion)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
    """, (eid, data.get("componente",""), data.get("descripcion_dano",""),
          int(data.get("requiere_cierre_flujo",0)),
          data.get("impacto_servicio",""), data.get("numero_suscriptores_afectados"),
          data.get("recursos_requeridos",""), data.get("tiempo_estimado_reparacion_horas"),
          data.get("fotos",""), session.get("usuario_id"), datetime.now().isoformat()))
    conn.commit(); conn.close()
    return jsonify({"ok": True, "id": cur.lastrowid}), 201


@em_bp.route("/api/eventos/<int:eid>/edan")
@login_requerido
def api_edan_evento(eid):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM evaluacion_danos WHERE evento_emergencia_id=? ORDER BY fecha_evaluacion",
        (eid,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ══════════════════════════════════════════════════════════════════
# PROYECTOS DE REDUCCIÓN DEL RIESGO (Tabla 20 PEC)
# ══════════════════════════════════════════════════════════════════
@em_bp.route("/api/proyectos_riesgo")
@login_requerido
def api_proyectos_riesgo():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM proyectos_riesgo ORDER BY plazo, inversion_estimada DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@em_bp.route("/api/proyectos_riesgo/<int:pid>", methods=["PUT"])
@login_requerido
def api_actualizar_proyecto_riesgo(pid):
    data = request.get_json() or {}
    conn = get_db()
    conn.execute("""UPDATE proyectos_riesgo
        SET inversion_ejecutada=COALESCE(?,inversion_ejecutada),
            porcentaje_avance=COALESCE(?,porcentaje_avance),
            fecha_fin_real=COALESCE(?,fecha_fin_real),
            evidencias=COALESCE(?,evidencias)
        WHERE id=?""",
        (data.get("inversion_ejecutada"), data.get("porcentaje_avance"),
         data.get("fecha_fin_real"), data.get("evidencias"), pid))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════
# SIMULACROS
# ══════════════════════════════════════════════════════════════════
@em_bp.route("/api/simulacros", methods=["GET"])
@login_requerido
def api_simulacros():
    conn = get_db()
    rows = conn.execute("SELECT * FROM simulacros ORDER BY fecha DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@em_bp.route("/api/simulacros", methods=["POST"])
@login_requerido
def api_crear_simulacro():
    data = request.get_json() or {}
    conn = get_db()
    cur  = conn.execute("""
        INSERT INTO simulacros(nombre,tipo_evento,fecha,duracion_minutos,
            participantes,evaluacion,lecciones,responsable_id)
        VALUES(?,?,?,?,?,?,?,?)
    """, (data.get("nombre",""), data.get("tipo_evento",""),
          data.get("fecha", datetime.now().date().isoformat()),
          data.get("duracion_minutos"), data.get("participantes"),
          data.get("evaluacion",""), data.get("lecciones",""),
          session.get("usuario_id")))
    conn.commit(); conn.close()
    return jsonify({"ok": True, "id": cur.lastrowid}), 201


# ══════════════════════════════════════════════════════════════════
# DASHBOARD PEC
# ══════════════════════════════════════════════════════════════════
@em_bp.route("/api/dashboard")
@login_requerido
def api_dashboard():
    conn = get_db()
    ul   = conn.execute("SELECT * FROM niveles_quebrada ORDER BY fecha DESC LIMIT 1").fetchone()
    ev   = conn.execute("SELECT COUNT(*) as c FROM eventos_emergencia WHERE fecha_fin IS NULL").fetchone()["c"]
    rr   = conn.execute("SELECT prioridad,COUNT(*) as c FROM riesgos_pec GROUP BY prioridad").fetchall()
    rs   = conn.execute("SELECT estado,COUNT(*) as c FROM recursos_emergencia GROUP BY estado").fetchall()
    pa   = conn.execute("SELECT AVG(porcentaje_avance) as avg FROM proyectos_riesgo").fetchone()["avg"]
    conn.close()
    return jsonify({
        "ultimo_nivel":              dict(ul) if ul else None,
        "eventos_abiertos":          ev,
        "riesgos":                   {r["prioridad"]: r["c"] for r in rr},
        "recursos":                  {r["estado"]: r["c"] for r in rs},
        "proyectos_riesgo_avance":   round(pa or 0, 1),
    })


# ══════════════════════════════════════════════════════════════════
# GENERACIÓN EXCEL — LISTADO DE RIESGOS (PEC)
# ══════════════════════════════════════════════════════════════════
@em_bp.route("/api/riesgos/informe_excel")
@login_requerido
def api_informe_riesgos_excel():
    """Excel completo del listado de riesgos — formato PEC SIGCA."""
    import pandas as pd
    from openpyxl.styles import (Font, PatternFill, Alignment,
                                  Border, Side, numbers)
    from openpyxl.utils import get_column_letter

    anio = request.args.get("anio", datetime.now().year)
    conn = get_db()
    riesgos = conn.execute(
        "SELECT * FROM riesgos_pec ORDER BY codigo"
    ).fetchall()
    cfg_bd  = conn.execute("SELECT * FROM configuracion WHERE clave IN "
        "('nombre_asociacion','nit','municipio','representante_legal')").fetchall()
    conn.close()
    cfg = {r["clave"]: r["valor"] for r in cfg_bd}

    output = BytesIO()
    C_AZUL  = "1E3A8A"; C_VERDE = "0F6E56"; C_ROJO = "991B1B"
    C_AMAR  = "92400E"; C_BLAN  = "FFFFFF"; C_GRIS = "F1F5F9"
    azul_f  = PatternFill("solid", fgColor=C_AZUL)
    gris_f  = PatternFill("solid", fgColor=C_GRIS)
    rojo_f  = PatternFill("solid", fgColor="FEE2E2")
    amar_f  = PatternFill("solid", fgColor="FEF3C7")
    verd_f  = PatternFill("solid", fgColor="D1FAE5")

    borde = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    from openpyxl import Workbook
    wb = Workbook()

    # ── Hoja 1: Listado completo de riesgos ──────────────────────
    ws = wb.active
    ws.title = f"Riesgos PEC {anio}"
    ws.sheet_view.showGridLines = False

    # Título
    ws.merge_cells("A1:X1")
    ws["A1"] = f"LISTADO DE RIESGOS — PLAN DE EMERGENCIAS Y CONTINGENCIAS {anio}"
    ws["A1"].font = Font(name="Calibri", size=14, bold=True, color=C_AZUL)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    ws.merge_cells("A2:X2")
    nombre = cfg.get("nombre_asociacion","SIGCA")
    nit    = cfg.get("nit","832.001.389-2")
    ws["A2"] = f"{nombre} — NIT {nit} — Villeta, Cundinamarca | Fórmula PEC: V = (Ia×10% + It×80% + Ic×0% + Iq×10%) × P"
    ws["A2"].font = Font(name="Calibri", size=9, italic=True, color="64748B")
    ws["A2"].alignment = Alignment(horizontal="center")
    ws.row_dimensions[2].height = 16

    # Cabecera
    CABECERAS = [
        "ID","Riesgo / Amenaza","Tipo","Categoría",
        "Prob.(P)","Imp.Alcance(Ia)","Imp.Tiempo(It)","Imp.Costo(Ic)","Imp.Calidad(Iq)",
        "V.Global","Prioridad",
        "Afecta\nAlcance","Afecta\nTiempo","Afecta\nCosto","Afecta\nCalidad",
        "Directo","Indirecto",
        "Dueño","Plan de Respuesta","¿Activado?","Estado",
        "Evidencia","Justificación Técnica","Juicio Experto"
    ]
    ws.row_dimensions[4].height = 45
    for col, cab in enumerate(CABECERAS, 1):
        cell = ws.cell(row=4, column=col, value=cab)
        cell.font      = Font(name="Calibri", size=9, bold=True, color=C_BLAN)
        cell.fill      = azul_f
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border    = borde

    # Datos
    resumen = {"Alta": 0, "Media": 0, "Baja": 0}
    for i, r in enumerate(riesgos):
        fila = i + 5
        pri  = r["prioridad"] or "Baja"
        resumen[pri] = resumen.get(pri, 0) + 1
        fill = rojo_f if pri=="Alta" else amar_f if pri=="Media" else verd_f
        vals = [
            r["codigo"], r["nombre"], r["tipo"] or "", r["categoria"] or "",
            r["probabilidad"], r["impacto_alcance"], r["impacto_tiempo"],
            r["impacto_costo"], r["impacto_calidad"],
            r["valoracion_global"], pri,
            "✓" if r["afecta_alcance"] else "", "✓" if r["afecta_tiempo"] else "",
            "✓" if r["afecta_costo"]   else "", "✓" if r["afecta_calidad"] else "",
            "✓" if r["impacto_directo"] else "", "✓" if r["impacto_indirecto"] else "",
            r["dueno"] or "", r["plan_respuesta"] or "",
            "SÍ" if r["activado"] else "No", r["estado"] or "",
            r["justificacion_evidencia"] or "",
            r["justificacion_tecnica"]   or "",
            r["justificacion_juicio_experto"] or "",
        ]
        ws.row_dimensions[fila].height = 45
        for col, val in enumerate(vals, 1):
            cell = ws.cell(row=fila, column=col, value=val)
            cell.font      = Font(name="Calibri", size=8)
            cell.fill      = fill
            cell.border    = borde
            cell.alignment = Alignment(horizontal="center" if col in [1,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,20,21]
                                       else "left", vertical="center", wrap_text=True)
            if col == 10:  # V.Global
                cell.font = Font(name="Calibri", size=9, bold=True)
                cell.number_format = "0.0000"
            if col == 11:  # Prioridad
                cell.font = Font(name="Calibri", size=9, bold=True,
                                  color=C_ROJO if pri=="Alta" else C_AMAR if pri=="Media" else C_VERDE)

    # Anchos de columna
    anchos = [6,40,10,22,7,9,9,8,9,9,10,7,7,7,8,7,8,20,45,8,14,35,35,35]
    for col, ancho in enumerate(anchos, 1):
        ws.column_dimensions[get_column_letter(col)].width = ancho

    # ── Hoja 2: Parámetros de la fórmula ────────────────────────
    ws2 = wb.create_sheet("Parámetros PEC")
    ws2["A1"] = "PARÁMETROS DE VALORACIÓN — PEC SIGCA"
    ws2["A1"].font = Font(name="Calibri", size=13, bold=True, color=C_AZUL)
    ws2.column_dimensions["A"].width = 35
    ws2.column_dimensions["B"].width = 20

    params = [
        ["",""],
        ["FÓRMULA","V = (Ia×Pond.A + It×Pond.T + Ic×Pond.C + Iq×Pond.Q) × P"],
        ["",""],
        ["Ponderación Alcance (Pond.A)","10%"],
        ["Ponderación Tiempo (Pond.T)","80%   ← CRÍTICO"],
        ["Ponderación Costo (Pond.C)","0%"],
        ["Ponderación Calidad (Pond.Q)","10%"],
        ["",""],
        ["SEMÁFORO",""],
        ["🔴 Alta (intervención inmediata)","V ≥ 0.50"],
        ["🟡 Media (monitoreo continuo)","0.25 ≤ V < 0.50"],
        ["🟢 Baja (aceptable)","V < 0.25"],
        ["",""],
        ["RESUMEN DE ESTE PEC",""],
        ["Total riesgos", str(len(riesgos))],
        ["Alta prioridad 🔴", str(resumen["Alta"])],
        ["Media prioridad 🟡", str(resumen["Media"])],
        ["Baja prioridad 🟢", str(resumen["Baja"])],
        ["",""],
        ["Generado", datetime.now().strftime("%d/%m/%Y %H:%M")],
        ["Sistema", "PARAGUASMJ"],
    ]
    for fila, (a, b) in enumerate(params, 2):
        ws2.cell(row=fila, column=1, value=a).font = Font(bold=bool(a and (":" not in a or a.isupper())), name="Calibri", size=10)
        ws2.cell(row=fila, column=2, value=b).font = Font(name="Calibri", size=10)

    # ── Hoja 3: Riesgos por prioridad ────────────────────────────
    for pri, fill_c in [("Alta", rojo_f), ("Media", amar_f), ("Baja", verd_f)]:
        grupo = [r for r in riesgos if r["prioridad"]==pri]
        if not grupo: continue
        ws3 = wb.create_sheet(f"Riesgos {pri}")
        hdrs = ["ID","Riesgo","Prob.","V.Global","Plan de Respuesta","Estado","Dueño"]
        for col, h in enumerate(hdrs, 1):
            cell = ws3.cell(row=1, column=col, value=h)
            cell.font = Font(bold=True, color=C_BLAN, name="Calibri", size=10)
            cell.fill = azul_f; cell.border = borde
        for i, r in enumerate(grupo, 2):
            for col, val in enumerate([r["codigo"],r["nombre"],r["probabilidad"],
                                        r["valoracion_global"],r["plan_respuesta"],
                                        r["estado"],r["dueno"]], 1):
                cell = ws3.cell(row=i, column=col, value=val)
                cell.fill = fill_c; cell.border = borde
                cell.font = Font(name="Calibri", size=9)
        ws3.column_dimensions["A"].width = 6
        ws3.column_dimensions["B"].width = 45
        ws3.column_dimensions["E"].width = 50
        ws3.column_dimensions["F"].width = 16

    wb.save(output)
    output.seek(0)
    fname = f"ListadoRiesgos_PEC_SIGCA_{anio}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(output, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ══════════════════════════════════════════════════════════════════
# GENERACIÓN WORD — DOCUMENTO PEC ACTUALIZADO ANUAL
# ══════════════════════════════════════════════════════════════════
@em_bp.route("/api/riesgos/pec_word")
@login_requerido
def api_pec_word():
    """Genera el PEC actualizado en Word (.docx) para un año dado."""
    anio = request.args.get("anio", datetime.now().year)
    conn = get_db()
    riesgos  = conn.execute("SELECT * FROM riesgos_pec ORDER BY codigo").fetchall()
    recursos = conn.execute("SELECT * FROM recursos_emergencia ORDER BY categoria,nombre").fetchall()
    alertas  = conn.execute("SELECT * FROM config_alertas ORDER BY nivel_min_cm").fetchall()
    cfg_rows = conn.execute("SELECT clave,valor FROM configuracion").fetchall()
    conn.close()

    cfg = {r["clave"]: r["valor"] for r in cfg_rows}
    nombre   = cfg.get("nombre_asociacion", "SIGCA")
    nit      = cfg.get("nit", "832.001.389-2")
    municipio= cfg.get("municipio", "Villeta, Cundinamarca")
    rep_legal= cfg.get("representante_legal", "José Humberto Ramírez")
    eslogan  = cfg.get("eslogan", "Gestión comunitaria para el agua y el desarrollo sostenible")

    try:
        from core.logo_manager import membrete_docx, pie_pagina_html, obtener_logo
        from docx import Document
        from docx.shared import Pt, RGBColor, Cm, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
    except ImportError:
        return jsonify({"error": "python-docx no instalado. Ejecute: pip install python-docx"}), 500

    doc = Document()

    # Márgenes
    for section in doc.sections:
        section.top_margin    = Cm(2.5)
        section.bottom_margin = Cm(2.0)
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2.0)

    AZUL  = RGBColor(0x1E, 0x3A, 0x8A)
    VERDE = RGBColor(0x0F, 0x6E, 0x56)
    ROJO  = RGBColor(0x99, 0x1B, 0x1B)
    GRIS  = RGBColor(0x64, 0x74, 0x8B)

    def h1(texto, color=AZUL):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(texto)
        r.font.size = Pt(16); r.font.bold = True; r.font.color.rgb = color
        return p

    def h2(texto, color=VERDE):
        p = doc.add_paragraph()
        r = p.add_run(texto)
        r.font.size = Pt(13); r.font.bold = True; r.font.color.rgb = color
        return p

    def h3(texto):
        p = doc.add_paragraph()
        r = p.add_run(texto)
        r.font.size = Pt(11); r.font.bold = True; r.font.color.rgb = AZUL
        return p

    def body(texto):
        p = doc.add_paragraph(texto)
        p.runs[0].font.size = Pt(10) if p.runs else None
        return p

    # ── Portada ──────────────────────────────────────────────────
    doc.add_paragraph()
    h1(nombre.upper())
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"NIT {nit}"); r.font.size = Pt(11); r.font.color.rgb = GRIS

    doc.add_paragraph()
    h1(f"PLAN DE EMERGENCIAS Y CONTINGENCIAS", VERDE)
    h1(f"VERSIÓN {anio}")

    doc.add_paragraph()
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run(f'"{eslogan}"'); r2.font.italic = True; r2.font.size = Pt(10); r2.font.color.rgb = GRIS

    doc.add_paragraph()
    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = p3.add_run(f"Municipio de Villeta, Cundinamarca\n{municipio}")
    r3.font.size = Pt(10)

    doc.add_paragraph()
    p4 = doc.add_paragraph()
    p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r4 = p4.add_run(f"Generado: {datetime.now().strftime('%d de %B de %Y')}")
    r4.font.size = Pt(9); r4.font.color.rgb = GRIS

    doc.add_page_break()

    # ── I. Metodología de valoración ─────────────────────────────
    h2("I. METODOLOGÍA DE VALORACIÓN Y FÓRMULA DEL RIESGO")
    body("El presente PEC implementa una ecuación matricial paramétrica cuantitativa para calcular el nivel de riesgo antes de medidas de mitigación:")

    p_formula = doc.add_paragraph()
    r_f = p_formula.add_run("V = (Ia × 0.10  +  It × 0.80  +  Ic × 0.00  +  Iq × 0.10)  ×  P")
    r_f.font.size = Pt(13); r_f.font.bold = True; r_f.font.color.rgb = AZUL
    p_formula.alignment = WD_ALIGN_PARAGRAPH.CENTER

    body("Donde:\n• P = Probabilidad (0.1 a 1.0)\n• Ia = Impacto en Alcance | Peso: 10%\n• It = Impacto en Tiempo | Peso: 80% — CRÍTICO para continuidad del servicio\n• Ic = Impacto en Costo | Peso: 0%\n• Iq = Impacto en Calidad | Peso: 10%")

    h3("Semáforo de Priorización")
    t_sem = doc.add_table(rows=4, cols=3)
    t_sem.style = "Table Grid"
    hdrs_sem = ["Nivel","Criterio","Acción"]
    for i,h in enumerate(hdrs_sem):
        cell = t_sem.rows[0].cells[i]
        cell.text = h
        cell.paragraphs[0].runs[0].font.bold = True
    rows_sem = [
        ("🔴 ALTA (V ≥ 0.50)", "Intervención estructural prioritaria inmediata","Inversión presupuestal y reporte a entes externos"),
        ("🟡 MEDIA (V ≥ 0.25)","Monitoreo continuo y planes de mitigación parcial","Reporte mensual a Junta Directiva"),
        ("🟢 BAJA (V < 0.25)", "Riesgo bajo control operacional","Monitoreo periódico"),
    ]
    for i,(nivel,criterio,accion) in enumerate(rows_sem,1):
        t_sem.rows[i].cells[0].text = nivel
        t_sem.rows[i].cells[1].text = criterio
        t_sem.rows[i].cells[2].text = accion

    doc.add_paragraph()

    # ── II. Semáforo de caudal ────────────────────────────────────
    h2("II. PROTOCOLO DE ALERTA Y SEGUIMIENTO DEL CAUDAL")
    for nivel, datos in PROTOCOLO_ALERTA.items():
        icono = {"verde":"🟢","amarillo":"🟡","naranja":"🟠","rojo":"🔴"}[nivel]
        h3(f"{icono} NIVEL {nivel.upper()}")
        body(f"Situación: {datos['disminucion']}")
        body(f"Suspensión del servicio: {datos['suspension']}")
        body(f"Responsable: {datos['responsable']}")
        body(f"Acciones: {datos['acciones']}")
        doc.add_paragraph()

    doc.add_page_break()

    # ── III. Listado de riesgos ───────────────────────────────────
    h2(f"III. LISTADO DE RIESGOS — {anio}")
    body(f"Total de riesgos identificados: {len(riesgos)} | "
         f"Alta: {sum(1 for r in riesgos if r['prioridad']=='Alta')} 🔴 | "
         f"Media: {sum(1 for r in riesgos if r['prioridad']=='Media')} 🟡 | "
         f"Baja: {sum(1 for r in riesgos if r['prioridad']=='Baja')} 🟢")
    doc.add_paragraph()

    # Tabla de riesgos
    cols_r = ["ID","Riesgo / Amenaza","Tipo","Prob.","V.Global","Prioridad","Plan de Respuesta","Estado","Dueño"]
    t_r = doc.add_table(rows=1, cols=len(cols_r))
    t_r.style = "Table Grid"
    for i,h in enumerate(cols_r):
        cell = t_r.rows[0].cells[i]
        cell.text = h
        run  = cell.paragraphs[0].runs[0]
        run.font.bold = True; run.font.size = Pt(8); run.font.color.rgb = RGBColor(255,255,255)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    for r in riesgos:
        row = t_r.add_row()
        for i, val in enumerate([
            r["codigo"], r["nombre"], r["tipo"] or "",
            f"{float(r['probabilidad'] or 0):.2f}",
            f"{float(r['valoracion_global'] or 0):.4f}",
            r["prioridad"] or "",
            r["plan_respuesta"] or "", r["estado"] or "", r["dueno"] or ""
        ]):
            cell = row.cells[i]
            cell.text = str(val)
            cell.paragraphs[0].runs[0].font.size = Pt(8)
            cell.paragraphs[0].alignment = (
                WD_ALIGN_PARAGRAPH.CENTER if i in [0,2,3,4,5,7] else WD_ALIGN_PARAGRAPH.LEFT
            )

    doc.add_page_break()

    # ── IV. Inventario de recursos ────────────────────────────────
    h2("IV. INVENTARIO DE RECURSOS PARA EMERGENCIAS")
    categorias = {}
    for r in recursos:
        cat = r["categoria"] or "General"
        categorias.setdefault(cat, []).append(r)

    for cat, items in categorias.items():
        h3(f"▸ {cat}")
        t_inv = doc.add_table(rows=1, cols=4)
        t_inv.style = "Table Grid"
        for i,h in enumerate(["Recurso","Cantidad","Ubicación","Estado"]):
            cell = t_inv.rows[0].cells[i]
            cell.text = h
            cell.paragraphs[0].runs[0].font.bold = True
            cell.paragraphs[0].runs[0].font.size = Pt(8)
        for item in items:
            row = t_inv.add_row()
            for i,val in enumerate([item["nombre"],str(item["cantidad"]),
                                     item["ubicacion"] or "—",item["estado"] or "disponible"]):
                row.cells[i].text = val
                row.cells[i].paragraphs[0].runs[0].font.size = Pt(8)
        doc.add_paragraph()

    # ── V. Pie de firma ───────────────────────────────────────────
    doc.add_page_break()
    h2("V. APROBACIÓN Y FIRMAS")
    doc.add_paragraph()
    t_firm = doc.add_table(rows=2, cols=2)
    t_firm.style = "Table Grid"
    t_firm.rows[0].cells[0].text = f"_______________________________\n{rep_legal}\nRepresentante Legal\n{nombre}"
    t_firm.rows[0].cells[1].text = f"_______________________________\nJefe Operativo\n{nombre}"
    t_firm.rows[1].cells[0].text = f"Villeta, Cundinamarca — {datetime.now().strftime('%d/%m/%Y')}"
    t_firm.rows[1].cells[1].text = f"Versión PEC: {anio}"

    p_footer = doc.add_paragraph()
    p_footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ft = p_footer.add_run(f"Documento generado por PARAGUASMJ — {nombre} — NIT {nit}")
    r_ft.font.size = Pt(8); r_ft.font.color.rgb = GRIS
    r_ft2 = p_footer.add_run("\nSoporte Técnico y Código Core: M. Jiménez Ch.")
    r_ft2.font.size = Pt(7); r_ft2.font.color.rgb = GRIS

    output = BytesIO()
    doc.save(output)
    output.seek(0)
    fname = f"PEC_SIGCA_{anio}.docx"
    return send_file(output, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
