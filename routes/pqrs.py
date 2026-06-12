"""
routes/pqrs.py — PQRS + Órdenes de Trabajo + Actas + Bitácora (escaneo)

Codificación SIGCA:
  GC-PQR-AAAA-NNN → Gestión Comercial — PQRS
  GA-OT-AAAA-NNN  → Gestión Ambiental — Órdenes de Trabajo
  GA-ACT-AAAA-NNN → Gestión Ambiental — Actas de Ejecución
  GA-BIT-AAAA-NNN → Gestión Ambiental — Bitácoras escaneadas

Cumplimiento normativo:
  Res. SSPD 54575/2015 — Formato A, causales 01-99, canales 01-10
  Ley 142/1994 Art. 9  — Derechos de petición ESP
  Ley 1755/2015        — Plazos en días hábiles
  Res. CRA 943/2021    — Esquemas diferenciales rurales
"""
import os, logging as _logging
_log_pqrs = _logging.getLogger("sigca.pqrs")
from flask import (Blueprint, render_template, request, jsonify,
                   redirect, url_for, flash, session, send_file)
from werkzeug.utils import secure_filename
from core.database_manager import get_db, obtener_consecutivo
from core.seguridad import login_requerido
from utils.audit import log_action
from datetime import date, datetime, timedelta
from io import BytesIO

pqrs_bp = Blueprint("pqrs", __name__, url_prefix="/pqrs")

# ── Festivos Colombia (años 2025-2030) ──────────────────────────────
FESTIVOS_CO = {
    date(2026, 1, 1), date(2026, 1, 12), date(2026, 3, 23),
    date(2026, 4, 2),  date(2026, 4, 3),  date(2026, 5, 1),
    date(2026, 5, 25), date(2026, 6, 15), date(2026, 6, 22),
    date(2026, 6, 29), date(2026, 7, 20), date(2026, 8, 7),
    date(2026, 8, 17), date(2026, 10, 12),date(2026, 11, 2),
    date(2026, 11, 16),date(2026, 12, 8), date(2026, 12, 25),
    date(2025, 1, 1),  date(2025, 1, 6),  date(2025, 3, 24),
    date(2025, 4, 17), date(2025, 4, 18), date(2025, 5, 1),
    date(2025, 6, 2),  date(2025, 6, 23), date(2025, 6, 30),
    date(2025, 7, 20), date(2025, 8, 7),  date(2025, 8, 18),
    date(2025, 10, 13),date(2025, 11, 3), date(2025, 11, 17),
    date(2025, 12, 8), date(2025, 12, 25),
}


def _dias_habiles(desde: date, dias: int) -> date:
    """Calcula fecha límite en días HÁBILES (excluye fines de semana y festivos)."""
    actual, contados = desde, 0
    while contados < dias:
        actual += timedelta(days=1)
        if actual.weekday() < 5 and actual not in FESTIVOS_CO:
            contados += 1
    # Si cae en fin de semana o festivo, pasar al siguiente hábil
    while actual.weekday() >= 5 or actual in FESTIVOS_CO:
        actual += timedelta(days=1)
    return actual


# ── Tipos de PQR con plazos (Ley 1755/2015) ────────────────────────
TIPOS_PQR = {
    "Peticion":              {"plazo": 15, "codigo_sui": "1"},
    "Queja":                 {"plazo": 15, "codigo_sui": "2"},
    "Reclamo":               {"plazo": 15, "codigo_sui": "3"},
    "Recurso de Reposicion": {"plazo": 15, "codigo_sui": "4"},
    "Recurso de Apelacion":  {"plazo": 15, "codigo_sui": "4"},
    "Consulta":              {"plazo": 30, "codigo_sui": "5"},
    "Sugerencia":            {"plazo": 30, "codigo_sui": "6"},
    "Denuncia":              {"plazo": 15, "codigo_sui": "7"},
}

# ── Causales oficiales (Res. SSPD 54575/2015 — Tabla 1) ─────────────
CAUSALES = {
    "01": {"texto": "Facturación",            "tiene_subcausal": True},
    "02": {"texto": "Calidad del servicio",   "tiene_subcausal": False},
    "03": {"texto": "Suspensión del servicio","tiene_subcausal": False},
    "04": {"texto": "Conexión del servicio",  "tiene_subcausal": False},
    "05": {"texto": "Reconexión del servicio","tiene_subcausal": False},
    "06": {"texto": "Medidores",              "tiene_subcausal": False},
    "07": {"texto": "Contrato / Condiciones", "tiene_subcausal": False},
    "08": {"texto": "Atención al cliente",    "tiene_subcausal": False},
    "09": {"texto": "Daños a terceros",       "tiene_subcausal": False},
    "10": {"texto": "Cobros no reconocidos",  "tiene_subcausal": False},
    "11": {"texto": "Terminación del contrato","tiene_subcausal": False},
    "12": {"texto": "Cesión de inmueble",     "tiene_subcausal": False},
    "99": {"texto": "Otras causales",         "tiene_subcausal": False},
}

# ── Subcausales de facturación (Res. 54575/2015 — Tabla 2) ──────────
SUBCAUSALES_FACTURACION = {
    "01-01": "Lectura del medidor incorrecta",
    "01-02": "Tarifa aplicada incorrecta",
    "01-03": "Período de facturación incorrecto",
    "01-04": "Cálculo del consumo estimado",
    "01-05": "Consumo facturado sin medición",
    "01-06": "Desviación significativa de consumo",
    "01-99": "Otras causales de facturación",
}

# ── Canales de recepción (Res. 54575/2015) ──────────────────────────
CANALES = {
    "01": "Oficina física / Ventanilla",
    "02": "Línea de atención telefónica",
    "03": "Página web / Formulario en línea",
    "04": "Correo electrónico",
    "08": "Correspondencia física / Escrito",
    "09": "Ventanilla única / Traslado externo",
    "10": "Traslado por competencia SSPD",
    "99": "Otro canal",
}

# ── Servicios (Res. 54575/2015) ──────────────────────────────────────
SERVICIOS = {
    "1": "Acueducto (agua potable)",
    "2": "Alcantarillado",
    "99": "Otro",
}

# ── Estados PQR (Res. 54575/2015) ───────────────────────────────────
ESTADOS_SUI = {
    "1": "Recibida",
    "2": "En trámite",
    "3": "Resuelta",
    "4": "En recurso",
    "5": "Cerrada",
}

COMPONENTES = [
    "Bocatoma / Captación",
    "Línea de conducción / Aducción",
    "Planta de tratamiento (PTAP)",
    "Tanque de almacenamiento",
    "Red de distribución",
    "Acometida domiciliaria",
    "Medidor / Micromedición",
    "Facturación / Cobro",
    "Calidad del agua",
    "Atención al usuario",
    "Otro",
]

EXTS_BITACORA = {"pdf", "jpg", "jpeg", "png", "tif", "tiff"}
UPLOAD_BITACORA = os.path.join("uploads", "bitacoras")


# ══════════════════════════════════════════════════════════════════
# PANEL PRINCIPAL
# ══════════════════════════════════════════════════════════════════

@pqrs_bp.route("/")
@login_requerido
def listar():
    estado = request.args.get("estado", "")
    tipo   = request.args.get("tipo",   "")
    q      = request.args.get("q", "").strip()
    mes    = request.args.get("mes", "")
    conn   = get_db()

    sql = """
        SELECT p.pk_pqr_id as id,
               COALESCE(p.radicado_visible, r.codigo_completo) as radicado,
               COALESCE(p.resumen, p.descripcion_detallada) as resumen,
               p.tipo_pqr, p.estado_pqr, p.fecha_limite,
               p.canal_codigo, p.causal_codigo, p.causal_texto,
               p.servicio_codigo, p.reportado_sui,
               p.requiere_visita, p.en_segunda_instancia,
               r.fecha_radicacion, r.codigo_completo,
               c.razon_social as usuario_nombre, c.telefono,
               CASE WHEN p.fecha_limite < date('now')
                    AND p.estado_pqr NOT IN ('Resuelta','Cerrada','Archivada','Respondida')
                    THEN 1 ELSE 0 END as vencida,
               (SELECT COUNT(*) FROM ordenes_trabajo ot
                WHERE ot.pqrs_id = p.pk_pqr_id) as n_ordenes
        FROM pqrs p
        JOIN registro_central r ON p.fk_registro_id = r.pk_registro_id
        JOIN contactos c ON p.fk_suscriptor_id = c.pk_contacto_id
        WHERE 1=1
    """
    params = []
    if estado: sql += " AND p.estado_pqr=?"; params.append(estado)
    if tipo:   sql += " AND p.tipo_pqr=?";   params.append(tipo)
    if mes:    sql += " AND p.mes_reporte=?"; params.append(mes)
    if q:
        sql += " AND (r.codigo_completo LIKE ? OR c.razon_social LIKE ? OR p.resumen LIKE ?)"
        params.extend([f"%{q}%"] * 3)
    sql += " ORDER BY r.fecha_radicacion DESC"

    pqrs     = conn.execute(sql, params).fetchall()
    stats    = conn.execute(
        "SELECT estado_pqr, COUNT(*) as cnt FROM pqrs GROUP BY estado_pqr"
    ).fetchall()
    vencidas = conn.execute("""
        SELECT COUNT(*) as c FROM pqrs
        WHERE fecha_limite < date('now')
        AND estado_pqr NOT IN ('Resuelta','Cerrada','Archivada','Respondida')
    """).fetchone()["c"]
    no_reportadas = conn.execute(
        "SELECT COUNT(*) as c FROM pqrs WHERE reportado_sui=0 "
        "AND estado_pqr IN ('Cerrada','Resuelta','Respondida')"
    ).fetchone()["c"]
    conn.close()

    # Alerta día 15 del mes siguiente
    hoy       = date.today()
    dia_15    = date(hoy.year if hoy.month < 12 else hoy.year+1,
                     hoy.month+1 if hoy.month < 12 else 1, 15)
    dias_para_15 = (dia_15 - hoy).days

    return render_template("pqrs/lista.html",
                           pqrs=pqrs, stats=stats, vencidas=vencidas,
                           no_reportadas=no_reportadas,
                           dias_para_15=dias_para_15,
                           estado_sel=estado, tipo_sel=tipo, q=q,
                           tipos=list(TIPOS_PQR.keys()))


# ══════════════════════════════════════════════════════════════════
# NUEVA PQRS  →  GC-PQR-AAAA-NNN
# ══════════════════════════════════════════════════════════════════

@pqrs_bp.route("/nueva", methods=["GET", "POST"])
@login_requerido
def nueva():
    conn = get_db()
    if request.method == "POST":
        anio     = date.today().year
        tipo_pqr = request.form["tipo_pqr"]
        tipo_sol = request.form.get("tipo_solicitante","suscriptor")
        susc_id  = request.form.get("fk_suscriptor_id","0") or "0"

        # Suscriptor libre: registrar contacto temporal si no existe
        if tipo_sol == "usuario" or susc_id == "0":
            usr_nom = request.form.get("usuario_nombre","Ciudadano").strip() or "Ciudadano"
            usr_cel = request.form.get("usuario_telefono","")
            usr_ced = request.form.get("usuario_cedula","")
            _c = get_db()
            exist = _c.execute(
                "SELECT pk_contacto_id FROM contactos "
                "WHERE nit_cedula=? AND nit_cedula!='' LIMIT 1",
                (usr_ced,)
            ).fetchone() if usr_ced else None
            if exist:
                susc_id = str(exist["pk_contacto_id"])
            else:
                _cur = _c.execute(
                    "INSERT INTO contactos "
                    "(razon_social,nit_cedula,telefono,tipo_contacto,activo,activo_desactivo) "
                    "VALUES (?,?,?,'usuario',1,1)",
                    (usr_nom, usr_ced, usr_cel)
                )
                _c.commit()
                susc_id = str(_cur.lastrowid)
            _c.close()

        canal_cod = request.form.get("canal_codigo", "99")
        causal_cod = request.form.get("causal_codigo", "99")
        subcausal_cod = request.form.get("subcausal_codigo", "")
        servicio_cod = request.form.get("servicio_codigo", "1")
        resumen  = request.form.get("resumen", "").strip()
        detalle  = request.form.get("descripcion_detallada", "")
        comp     = request.form.get("componente_afectado", "")
        req_vis  = 1 if request.form.get("requiere_visita") else 0

        cfg_tipo = TIPOS_PQR.get(tipo_pqr, {"plazo": 15})
        plazo    = cfg_tipo["plazo"]
        # Calcular en días HÁBILES (Ley 1755/2015)
        fecha_lim = _dias_habiles(date.today(), plazo).isoformat()

        # Mes de reporte SUI (mes siguiente)
        hoy = date.today()
        mes_rep = f"{hoy.year if hoy.month < 12 else hoy.year+1}-{hoy.month+1:02d if hoy.month < 12 else '01'}"

        try:
            consec = obtener_consecutivo("GC", "PQR", anio)
            codigo = f"GC-PQR-{anio}-{consec:03d}"

            conn.execute("""
                INSERT INTO registro_central
                (codigo_completo, area, tipo_documento, anio, consecutivo,
                 fecha_radicacion, asunto_resumen, estado, creado_por)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (codigo, "GC", "PQR", anio, consec,
                  date.today().isoformat(),
                  f"{tipo_pqr}: {resumen[:80]}", "Recibida",
                  session.get("nombre_usuario")))
            reg_id = conn.execute(
                "SELECT last_insert_rowid() as id").fetchone()["id"]

            conn.execute("""
                INSERT INTO pqrs
                (fk_registro_id, tipo_pqr, fk_suscriptor_id,
                 medio_recepcion, canal_codigo,
                 causal_codigo, causal_texto,
                 subcausal_codigo, subcausal_texto,
                 servicio_codigo,
                 estado_pqr, fecha_limite,
                 descripcion_detallada, radicado_visible,
                 resumen, componente_afectado,
                 requiere_visita, mes_reporte)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (reg_id, tipo_pqr, susc_id,
                  CANALES.get(canal_cod, canal_cod), canal_cod,
                  causal_cod, CAUSALES.get(causal_cod, {}).get("texto",""),
                  subcausal_cod,
                  SUBCAUSALES_FACTURACION.get(subcausal_cod,""),
                  servicio_cod,
                  "Recibida", fecha_lim,
                  detalle, codigo, resumen, comp,
                  req_vis, mes_rep))
            conn.commit()

            log_action(accion="CREATE", modulo="pqrs",
                       descripcion=f"{codigo} — {tipo_pqr} — causal {causal_cod} — {resumen[:40]}")
            flash(f"✅ {tipo_pqr} radicada: {codigo}. "
                  f"Plazo: {plazo} días hábiles ({fecha_lim}).", "success")

            pid = conn.execute(
                "SELECT pk_pqr_id FROM pqrs WHERE fk_registro_id=?",
                (reg_id,)).fetchone()["pk_pqr_id"]
            conn.close()
            return redirect(url_for("pqrs.ver", pid=pid))
        except Exception as e:
            conn.rollback()
            _log_pqrs.error("nueva PQRS: %s", e, exc_info=True)
            flash("Error al registrar la PQRS. Contacte al administrador.", "danger")

    suscriptores = conn.execute(
        "SELECT pk_contacto_id, razon_social, telefono, direccion_predio as direccion "
        "FROM contactos WHERE activo=1 ORDER BY razon_social"
    ).fetchall()
    conn.close()
    return render_template("pqrs/nueva.html",
                           suscriptores=suscriptores,
                           tipos=TIPOS_PQR,
                           causales=CAUSALES,
                           subcausales=SUBCAUSALES_FACTURACION,
                           canales=CANALES,
                           servicios=SERVICIOS,
                           componentes=COMPONENTES)


# ══════════════════════════════════════════════════════════════════
# VER PQRS
# ══════════════════════════════════════════════════════════════════

@pqrs_bp.route("/<int:pid>")
@login_requerido
def ver(pid):
    conn = get_db()
    pqr  = conn.execute("""
        SELECT p.*, r.fecha_radicacion, r.codigo_completo,
               c.razon_social as usuario_nombre, c.telefono,
               c.direccion_predio as direccion, c.correo
        FROM pqrs p
        JOIN registro_central r ON p.fk_registro_id = r.pk_registro_id
        JOIN contactos c ON p.fk_suscriptor_id = c.pk_contacto_id
        WHERE p.pk_pqr_id=?
    """, (pid,)).fetchone()
    if not pqr:
        flash("PQRS no encontrada", "danger")
        return redirect(url_for("pqrs.listar"))

    ordenes = conn.execute("""
        SELECT ot.*, r.codigo_completo as codigo_ot,
               (SELECT COUNT(*) FROM actas_ejecucion a
                WHERE a.fk_ot_id=ot.pk_ot_id) as n_actas
        FROM ordenes_trabajo ot
        JOIN registro_central r ON ot.fk_registro_id=r.pk_registro_id
        WHERE ot.pqrs_id=? ORDER BY ot.pk_ot_id
    """, (pid,)).fetchall()

    actas = conn.execute("""
        SELECT a.*, r.codigo_completo as codigo_ot
        FROM actas_ejecucion a
        JOIN ordenes_trabajo ot ON a.fk_ot_id=ot.pk_ot_id
        JOIN registro_central r ON ot.fk_registro_id=r.pk_registro_id
        WHERE ot.pqrs_id=? ORDER BY a.fecha_ejecucion
    """, (pid,)).fetchall()

    tecnicos  = conn.execute(
        "SELECT pk_usuario_id, nombre_completo FROM usuarios "
        "WHERE activo=1 ORDER BY nombre_completo").fetchall()
    proyectos = conn.execute(
        "SELECT pk_proyecto_id as id, codigo, nombre FROM proyectos "
        "WHERE estado IN ('activo','planificacion') ORDER BY nombre").fetchall()
    conn.close()

    return render_template("pqrs/ver.html",
                           pqr=pqr, ordenes=ordenes, actas=actas,
                           tecnicos=tecnicos, proyectos=proyectos,
                           causales=CAUSALES, estados_sui=ESTADOS_SUI,
                           componentes=COMPONENTES)


# ══════════════════════════════════════════════════════════════════
# REGISTRAR RECURSO (segunda instancia)
# ══════════════════════════════════════════════════════════════════

@pqrs_bp.route("/<int:pid>/recurso", methods=["POST"])
@login_requerido
def registrar_recurso(pid):
    data = request.get_json() or {}
    conn = get_db()
    fecha_lim = _dias_habiles(date.today(), 15).isoformat()
    conn.execute("""
        UPDATE pqrs SET
            estado_pqr='En recurso',
            en_segunda_instancia=1,
            fecha_recurso=?,
            tipo_recurso=?,
            fecha_limite=?
        WHERE pk_pqr_id=?
    """, (date.today().isoformat(),
          data.get("tipo_recurso", "Reposicion"),
          fecha_lim, pid))
    conn.execute("""
        UPDATE registro_central SET estado='En recurso'
        WHERE pk_registro_id=(
            SELECT fk_registro_id FROM pqrs WHERE pk_pqr_id=?)
    """, (pid,))
    conn.commit(); conn.close()
    log_action(accion="RECURSO", modulo="pqrs",
               descripcion=f"PQRS {pid} — recurso de {data.get('tipo_recurso')}")
    return jsonify({"ok": True, "nueva_fecha_limite": fecha_lim})


# ══════════════════════════════════════════════════════════════════
# EMITIR ORDEN DE TRABAJO  →  GA-OT-AAAA-NNN
# ══════════════════════════════════════════════════════════════════

@pqrs_bp.route("/<int:pid>/orden", methods=["POST"])
@login_requerido
def emitir_orden(pid):
    data  = request.get_json() or {}
    conn  = get_db()
    anio  = date.today().year
    consec = obtener_consecutivo("GA", "OT", anio)
    num_ot = f"GA-OT-{anio}-{consec:03d}"

    try:
        conn.execute("""
            INSERT INTO registro_central
            (codigo_completo, area, tipo_documento, anio, consecutivo,
             fecha_radicacion, asunto_resumen, estado, creado_por)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (num_ot, "GA", "OT", anio, consec,
              date.today().isoformat(),
              f"OT: {data.get('descripcion_trabajo','')[:60]}",
              "Emitida", session.get("nombre_usuario")))
        reg_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]

        conn.execute("""
            INSERT INTO ordenes_trabajo
            (fk_registro_id, pqrs_id, numero_orden, tipo_servicio,
             prioridad, tecnico_asignado, descripcion_tareas, materiales,
             fecha_estimada, estado_ot)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (reg_id, pid, num_ot,
              data.get("tipo_servicio", "Correctivo"),
              data.get("prioridad", "normal"),
              data.get("tecnico_asignado", ""),
              data.get("descripcion_trabajo", ""),
              data.get("materiales", ""),
              data.get("fecha_estimada"),
              "Pendiente"))

        if data.get("proyecto_id"):
            conn.execute("""
                INSERT OR IGNORE INTO documentos_proyecto
                (documento_id, proyecto_id, tipo_relacion)
                VALUES (?,?,?)
            """, (reg_id, data["proyecto_id"], "soporte"))

        conn.execute(
            "UPDATE pqrs SET estado_pqr='En trámite' WHERE pk_pqr_id=?", (pid,))
        conn.execute("""
            UPDATE registro_central SET estado='En trámite'
            WHERE pk_registro_id=(
                SELECT fk_registro_id FROM pqrs WHERE pk_pqr_id=?)
        """, (pid,))
        conn.commit()
        log_action(accion="CREATE_OT", modulo="pqrs",
                   descripcion=f"{num_ot} → PQRS {pid}")
        conn.close()
        return jsonify({"ok": True, "codigo_ot": num_ot}), 201
    except Exception as e:
        conn.rollback(); conn.close()
        return jsonify({"ok": False, "error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════
# REGISTRAR ACTA  →  GA-ACT-AAAA-NNN
# ══════════════════════════════════════════════════════════════════

@pqrs_bp.route("/ot/<int:ot_id>/acta", methods=["POST"])
@login_requerido
def registrar_acta(ot_id):
    data = request.get_json() or {}
    conn = get_db()
    anio = date.today().year

    try:
        ot = conn.execute(
            "SELECT pqrs_id, fk_registro_id FROM ordenes_trabajo WHERE pk_ot_id=?",
            (ot_id,)).fetchone()
        if not ot:
            conn.close()
            return jsonify({"ok": False, "error": "OT no encontrada"}), 404

        consec    = obtener_consecutivo("GA", "ACT", anio)
        cod_act   = f"GA-ACT-{anio}-{consec:03d}"

        conn.execute("""
            INSERT INTO registro_central
            (codigo_completo, area, tipo_documento, anio, consecutivo,
             fecha_radicacion, asunto_resumen, estado, creado_por)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (cod_act, "GA", "ACT", anio, consec,
              date.today().isoformat(),
              f"Acta ejecución OT {ot_id}", "Registrada",
              session.get("nombre_usuario")))
        reg_acta = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]

        conn.execute("""
            INSERT INTO actas_ejecucion
            (fk_ot_id, fecha_ejecucion, hora_inicio, hora_fin,
             tareas_realizadas, materiales_utilizados,
             pruebas_presion, pruebas_cloro,
             observaciones, novedades,
             conformidad_usuario, verificado_supervisor, estado_acta)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?)
        """, (ot_id,
              data.get("fecha_ejecucion", date.today().isoformat()),
              data.get("hora_inicio",""), data.get("hora_fin",""),
              data.get("tareas_realizadas",""),
              data.get("materiales_utilizados",""),
              data.get("pruebas_presion",""), data.get("pruebas_cloro",""),
              data.get("observaciones",""), data.get("novedades",""),
              int(data.get("conformidad_usuario", 0)), "Registrada"))

        conn.execute(
            "UPDATE ordenes_trabajo SET estado_ot='Ejecutada', "
            "fecha_ejecucion=? WHERE pk_ot_id=?",
            (date.today().isoformat(), ot_id))

        conf = data.get("conformidad_usuario")
        if conf and ot["pqrs_id"]:
            conn.execute("""
                UPDATE pqrs SET estado_pqr='Resuelta',
                    conformidad_usuario=1, fecha_respuesta_real=?
                WHERE pk_pqr_id=?
            """, (date.today().isoformat(), ot["pqrs_id"]))
            conn.execute("""
                UPDATE registro_central SET estado='Resuelta'
                WHERE pk_registro_id=(
                    SELECT fk_registro_id FROM pqrs WHERE pk_pqr_id=?)
            """, (ot["pqrs_id"],))

        # Vincular acta al mismo proyecto de la OT
        proy = conn.execute(
            "SELECT proyecto_id FROM documentos_proyecto WHERE documento_id=?",
            (ot["fk_registro_id"],)).fetchone()
        if proy:
            conn.execute("""
                INSERT OR IGNORE INTO documentos_proyecto
                (documento_id, proyecto_id, tipo_relacion)
                VALUES (?,?,?)
            """, (reg_acta, proy["proyecto_id"], "soporte"))

        conn.commit()
        log_action(accion="CREATE_ACTA", modulo="pqrs",
                   descripcion=f"{cod_act} — OT {ot_id}")
        conn.close()
        return jsonify({"ok": True, "codigo_acta": cod_act}), 201
    except Exception as e:
        conn.rollback(); conn.close()
        return jsonify({"ok": False, "error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════
# VERIFICACIÓN SUPERVISOR
# ══════════════════════════════════════════════════════════════════

@pqrs_bp.route("/acta/<int:acta_id>/verificar", methods=["POST"])
@login_requerido
def verificar_acta(acta_id):
    data     = request.get_json() or {}
    conforme = data.get("conforme", True)
    conn     = get_db()
    conn.execute("""
        UPDATE actas_ejecucion
        SET verificado_supervisor=1, fecha_verificacion=?,
            requiere_correccion=?, estado_acta=?
        WHERE pk_ae_id=?
    """, (datetime.now().isoformat(),
          0 if conforme else 1,
          "Verificada" if conforme else "Con observaciones",
          acta_id))
    if conforme:
        acta = conn.execute("""
            SELECT ot.pqrs_id FROM actas_ejecucion a
            JOIN ordenes_trabajo ot ON a.fk_ot_id=ot.pk_ot_id
            WHERE a.pk_ae_id=?
        """, (acta_id,)).fetchone()
        if acta and acta["pqrs_id"]:
            conn.execute("""
                UPDATE pqrs SET estado_pqr='Cerrada', notificado_usuario=1
                WHERE pk_pqr_id=?
            """, (acta["pqrs_id"],))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════
# BITÁCORA — SOLO ESCANEO DEL LIBRO FÍSICO  →  GA-BIT-AAAA-NNN
# ══════════════════════════════════════════════════════════════════

@pqrs_bp.route("/bitacora")
@login_requerido
def bitacora():
    conn = get_db()
    registros = conn.execute("""
        SELECT r.pk_registro_id as id, r.codigo_completo as codigo,
               r.fecha_radicacion, r.asunto_resumen as descripcion,
               r.estado, r.creado_por,
               a.nombre_archivo, a.ruta, a.tipo_archivo, a.tamano_bytes
        FROM registro_central r
        LEFT JOIN documentos_adjuntos a ON a.fk_registro_id=r.pk_registro_id
        WHERE r.area='GA' AND r.tipo_documento='BIT'
        ORDER BY r.fecha_radicacion DESC
    """).fetchall()
    fontaneros = conn.execute(
        "SELECT pk_usuario_id, nombre_completo FROM usuarios "
        "WHERE activo=1 ORDER BY nombre_completo").fetchall()
    conn.close()
    return render_template("pqrs/bitacora.html",
                           registros=registros, fontaneros=fontaneros)


@pqrs_bp.route("/bitacora/subir", methods=["POST"])
@login_requerido
def subir_bitacora():
    archivo     = request.files.get("archivo")
    fecha_bit   = request.form.get("fecha_bitacora", date.today().isoformat())
    fontanero   = request.form.get("fontanero", "")
    periodo     = request.form.get("periodo", "")
    descripcion = request.form.get("descripcion", "").strip()

    if not archivo or not archivo.filename:
        return jsonify({"ok": False, "error": "Seleccione un archivo"}), 400
    ext = archivo.filename.rsplit(".", 1)[-1].lower()
    if ext not in EXTS_BITACORA:
        return jsonify({"ok": False,
                        "error": f"Solo PDF, JPG, PNG o TIF"}), 400

    conn  = get_db()
    anio  = date.today().year
    consec = obtener_consecutivo("GA", "BIT", anio)
    codigo = f"GA-BIT-{anio}-{consec:03d}"
    asunto = descripcion or f"Bitácora {fontanero} — {periodo or fecha_bit}"

    try:
        os.makedirs(UPLOAD_BITACORA, exist_ok=True)
        fn = secure_filename(f"{codigo}_{fontanero.replace(' ','_')}.{ext}")
        ruta = os.path.join(UPLOAD_BITACORA, fn)
        archivo.save(ruta)

        conn.execute("""
            INSERT INTO registro_central
            (codigo_completo, area, tipo_documento, anio, consecutivo,
             fecha_radicacion, asunto_resumen, estado, creado_por)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (codigo, "GA", "BIT", anio, consec,
              fecha_bit, asunto, "Archivado",
              session.get("nombre_usuario")))
        reg_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]

        conn.execute("""
            INSERT INTO documentos_adjuntos
            (fk_registro_id, nombre_archivo, ruta, tipo_archivo,
             tamano_bytes, fecha_subida, subido_por)
            VALUES (?,?,?,?,?,?,?)
        """, (reg_id, fn, ruta,
              "application/pdf" if ext=="pdf" else f"image/{ext}",
              os.path.getsize(ruta), datetime.now().isoformat(),
              session.get("nombre_usuario")))

        conn.commit()
        log_action(accion="UPLOAD_BITACORA", modulo="pqrs",
                   descripcion=f"{codigo} — {fontanero}")
        conn.close()
        return jsonify({"ok": True, "codigo": codigo}), 201
    except Exception as e:
        conn.rollback(); conn.close()
        return jsonify({"ok": False, "error": str(e)}), 500


@pqrs_bp.route("/bitacora/<int:reg_id>/descargar")
@login_requerido
def descargar_bitacora(reg_id):
    conn = get_db()
    adj  = conn.execute(
        "SELECT ruta, nombre_archivo, tipo_archivo FROM documentos_adjuntos "
        "WHERE fk_registro_id=? LIMIT 1", (reg_id,)).fetchone()
    conn.close()
    if not adj or not os.path.exists(adj["ruta"]):
        flash("Archivo no encontrado", "danger")
        return redirect(url_for("pqrs.bitacora"))
    return send_file(adj["ruta"], as_attachment=True,
                     download_name=adj["nombre_archivo"],
                     mimetype=adj["tipo_archivo"])


# ══════════════════════════════════════════════════════════════════
# EXPORTAR FORMATO A — Res. 54575/2015 (para SUI)
# ══════════════════════════════════════════════════════════════════

@pqrs_bp.route("/exportar_sui")
@login_requerido
def exportar_sui():
    """
    Genera el Formato A de la Res. SSPD 54575/2015 listo para cargar al SUI.
    Hoja 1: Formato A — 10 columnas exactas en orden oficial
    Hoja 2: Detalle Completo — para uso interno SIGCA
    Hoja 3: Instrucciones — guía paso a paso para el operador
    """
    import pandas as pd
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    anio = request.args.get("anio", date.today().year)
    mes  = request.args.get("mes", "")

    conn = get_db()
    cfg  = {r["clave"]: r["valor"] for r in
            conn.execute("SELECT clave,valor FROM configuracion").fetchall()}

    sql = """
        SELECT
            r.codigo_completo, r.fecha_radicacion,
            p.tipo_pqr,
            COALESCE(p.causal_codigo,'99')    as causal_codigo,
            COALESCE(p.subcausal_codigo,'')   as subcausal_codigo,
            COALESCE(p.canal_codigo,'99')     as canal_codigo,
            COALESCE(p.servicio_codigo,'1')   as servicio_codigo,
            p.estado_pqr, p.fecha_respuesta_real,
            p.mes_reporte, p.reportado_sui,
            c.razon_social, c.nit_cedula
        FROM pqrs p
        JOIN registro_central r ON p.fk_registro_id=r.pk_registro_id
        JOIN contactos c ON p.fk_suscriptor_id=c.pk_contacto_id
        WHERE r.anio=?
    """
    params = [anio]
    if mes:
        sql += " AND p.mes_reporte=?"; params.append(mes)
    sql += " ORDER BY r.fecha_radicacion"
    rows = conn.execute(sql, params).fetchall()

    # Valores de empresa
    codigo_dane  = cfg.get("codigo_municipio", "25258")
    tipo_id_emp  = cfg.get("tipo_id_empresa",  "NUAP")
    nit_emp      = cfg.get("nit",              "")
    nit_limpio   = "".join(d for d in nit_emp if d.isdigit())

    # Mapeo estado interno → código SUI
    mapa_estados = {
        "Recibida":"1", "En trámite":"2", "En proceso":"2",
        "Resuelta":"3", "Respondida":"3",
        "En recurso":"4",
        "Cerrada":"5", "Archivada":"5",
    }

    def _fmt(f):
        """YYYY-MM-DD → DD-MM-YYYY (formato SUI)."""
        if not f: return ""
        try:
            p = str(f)[:10].split("-")
            return f"{p[2]}-{p[1]}-{p[0]}" if len(p) == 3 else str(f)[:10]
        except Exception:
            return str(f)[:10]

    # Construir filas
    COLS_SUI = ["Código_DANE","Tipo_ID","Número_ID","Servicio",
                "Canal","Causal","Subcausal","Estado_SUI",
                "Fecha_Recepcion","Fecha_Respuesta"]

    filas_sui  = []
    filas_comp = []
    for r in rows:
        causal   = r["causal_codigo"]   or "99"
        canal    = r["canal_codigo"]    or "99"
        servicio = r["servicio_codigo"] or "1"
        subcausal = r["subcausal_codigo"] if causal == "01" else ""
        estado   = mapa_estados.get(r["estado_pqr"], "2")

        fila_sui = {
            "Código_DANE":     codigo_dane,
            "Tipo_ID":         tipo_id_emp,
            "Número_ID":       nit_limpio,
            "Servicio":        servicio,
            "Canal":           canal,
            "Causal":          causal,
            "Subcausal":       subcausal,
            "Estado_SUI":      estado,
            "Fecha_Recepcion": _fmt(r["fecha_radicacion"]),
            "Fecha_Respuesta": _fmt(r["fecha_respuesta_real"]),
        }
        filas_sui.append(fila_sui)
        filas_comp.append({
            **fila_sui,
            "Radicado_GC-PQR": r["codigo_completo"],
            "Tipo_PQR":        r["tipo_pqr"],
            "Usuario":         r["razon_social"],
            "Estado_Interno":  r["estado_pqr"],
            "Causal_Texto":    CAUSALES.get(causal, {}).get("texto",""),
            "Canal_Texto":     CANALES.get(canal,""),
            "Mes_Reporte":     r["mes_reporte"] or "",
            "Ya_Reportado":    "Sí" if r["reportado_sui"] else "No",
        })

    # ── Construir Excel PRIMERO — solo marcar reportadas si el archivo es exitoso ──
    output = BytesIO()
    AZUL   = "1E3A8A"; BLANC = "FFFFFF"
    azul_f = PatternFill("solid", fgColor=AZUL)
    cent   = Alignment(horizontal="center", vertical="center")

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        # Hoja 1: Formato A — SUI (solo las 10 columnas oficiales)
        df_sui = pd.DataFrame(filas_sui, columns=COLS_SUI)
        df_sui.to_excel(writer, sheet_name="Formato A — SUI", index=False)

        # Hoja 2: Detalle completo (uso interno SIGCA)
        df_comp = pd.DataFrame(filas_comp) if filas_comp else pd.DataFrame(columns=[
            "Código_DANE","Tipo_ID","Número_ID","Servicio","Canal","Causal","Subcausal",
            "Estado_SUI","Fecha_Recepcion","Fecha_Respuesta",
            "Radicado_GC-PQR","Tipo_PQR","Usuario","Estado_Interno",
            "Causal_Texto","Canal_Texto","Mes_Reporte","Ya_Reportado"])
        df_comp.to_excel(writer, sheet_name="Detalle Completo", index=False)

        # Estilo cabeceras en las dos hojas de datos
        for sheet_name in ["Formato A — SUI", "Detalle Completo"]:
            if sheet_name not in writer.book.sheetnames: continue
            ws = writer.book[sheet_name]
            for cell in ws[1]:
                cell.font      = Font(bold=True, color=BLANC, name="Calibri", size=10)
                cell.fill      = azul_f
                cell.alignment = cent
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(
                    max(len(str(c.value or "")) for c in col) + 4, 40)

        # Hoja 3: Instrucciones para el operador
        wb  = writer.book
        ws3 = wb.create_sheet("Instrucciones SUI")
        ws3.column_dimensions["A"].width = 28
        ws3.column_dimensions["B"].width = 62

        inst = [
            ("INSTRUCCIONES PARA CARGAR AL SUI — Res. SSPD 54575/2015", ""),
            ("", ""),
            ("PASO 1", "Ingrese a: http://sui.superservicios.gov.co"),
            ("PASO 2", "Módulo: 'Peticiones, Quejas y Recursos' (NO Proyectos de Inversión)"),
            ("PASO 3", f"Copie los datos de la hoja «Formato A — SUI» ({len(filas_sui)} registros)"),
            ("PASO 4", "Fecha límite de reporte: día 15 del mes siguiente"),
            ("", ""),
            ("=== COLUMNAS DEL FORMATO A ===", ""),
            ("Código_DANE",     f"{codigo_dane} (Villeta, Cundinamarca)"),
            ("Tipo_ID",         f"{tipo_id_emp} (acueducto comunitario rural)"),
            ("Número_ID",       f"{nit_limpio} (NIT sin puntos ni guiones)"),
            ("Servicio",        "1=Acueducto  |  2=Alcantarillado"),
            ("Canal",           "01=Oficina  02=Teléfono  04=Correo  08=Escrito  99=Otro"),
            ("Causal",          "01=Facturación  02=Calidad  03=Suspensión  06=Medidor  99=Otras"),
            ("Subcausal",       "Solo cuando Causal=01: 01-01 lectura  01-06 desviación  01-99 otras"),
            ("Estado_SUI",      "1=Recibida  2=En trámite  3=Resuelta  4=En recurso  5=Cerrada"),
            ("Fecha_Recepcion", "Formato DD-MM-YYYY"),
            ("Fecha_Respuesta", "Formato DD-MM-YYYY (vacío si aún no se ha respondido)"),
            ("", ""),
            ("=== PLAZOS LEGALES ===", ""),
            ("Petición / Queja / Reclamo",  "15 días HÁBILES — Ley 1755/2015"),
            ("Consulta / Sugerencia",       "30 días HÁBILES — Ley 1755/2015"),
            ("Recurso de Reposición",       "15 días HÁBILES (plazo se renueva)"),
            ("", ""),
            ("SILENCIO ADMINISTRATIVO",
             "Si no responde en el plazo → se entiende respuesta NEGATIVA"),
            ("SANCIÓN",
             "El usuario puede acudir a la SSPD y pueden multarle"),
        ]
        for i, (a, b) in enumerate(inst, 1):
            ws3.cell(i, 1, a)
            ws3.cell(i, 2, b)
            if "===" in a or i == 1:
                ws3.cell(i,1).font = Font(bold=True, color=AZUL, size=11 if i==1 else 10)

    output.seek(0)
    # SHA-256 del Excel para trazabilidad normativa
    import hashlib as _hl
    excel_bytes = output.getvalue()
    hash_excel  = _hl.sha256(excel_bytes).hexdigest()
    output.seek(0)

    # Solo marcamos reportadas DESPUÉS de que el Excel se generó correctamente
    n_marcadas = 0
    try:
        for r in rows:
            conn.execute(
                "UPDATE pqrs SET reportado_sui=1 "
                "WHERE fk_registro_id=("
                "SELECT pk_registro_id FROM registro_central WHERE codigo_completo=?)",
                (r["codigo_completo"],))
            n_marcadas += 1
        conn.commit()
        from utils.audit import log_action
        log_action(
            accion="SUI_EXPORTADO",
            modulo="pqrs",
            descripcion=(
                f"Formato A SUI exportado: {n_marcadas} PQRS marcadas | "
                f"Mes: {mes or date.today().strftime('%Y-%m')} | "
                f"SHA256: {hash_excel[:32]}..."
            )
        )
    except Exception as e_mark:
        conn.rollback()
        from utils.audit import log_action
        log_action(
            accion="SUI_FALLIDO",
            modulo="pqrs",
            descripcion=f"Error al marcar PQRS como reportadas al SUI: {e_mark}"
        )
    conn.close()
    mes_str = mes or date.today().strftime("%Y-%m")
    return send_file(output, as_attachment=True,
                     download_name=f"FormatoA_SUI_SIGCA_{mes_str}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@pqrs_bp.route("/api/stats")
@login_requerido
def api_stats():
    conn = get_db()
    por_estado     = conn.execute(
        "SELECT estado_pqr, COUNT(*) as c FROM pqrs GROUP BY estado_pqr"
    ).fetchall()
    por_tipo       = conn.execute(
        "SELECT tipo_pqr, COUNT(*) as c FROM pqrs GROUP BY tipo_pqr"
    ).fetchall()
    por_causal     = conn.execute(
        "SELECT COALESCE(causal_codigo,'SN') as cod, "
        "COALESCE(causal_texto,'Sin causal') as txt, "
        "COUNT(*) as c FROM pqrs GROUP BY causal_codigo ORDER BY c DESC"
    ).fetchall()
    por_componente = conn.execute(
        "SELECT COALESCE(componente_afectado,'Sin clasificar') as comp, "
        "COUNT(*) as c FROM pqrs GROUP BY componente_afectado ORDER BY c DESC LIMIT 6"
    ).fetchall()
    vencidas = conn.execute("""
        SELECT COUNT(*) as c FROM pqrs
        WHERE fecha_limite < date('now')
        AND estado_pqr NOT IN ('Resuelta','Cerrada','Archivada','Respondida')
    """).fetchone()["c"]
    no_reportadas = conn.execute(
        "SELECT COUNT(*) as c FROM pqrs WHERE reportado_sui=0 "
        "AND estado_pqr IN ('Cerrada','Resuelta','Respondida')"
    ).fetchone()["c"]
    conn.close()
    return jsonify({
        "por_estado":      [dict(r) for r in por_estado],
        "por_tipo":        [dict(r) for r in por_tipo],
        "por_causal":      [dict(r) for r in por_causal],
        "por_componente":  [dict(r) for r in por_componente],
        "vencidas":        vencidas,
        "no_reportadas":   no_reportadas,
    })


@pqrs_bp.route("/api/causales")
@login_requerido
def api_causales():
    """Retorna causales y subcausales para el formulario dinámico."""
    return jsonify({
        "causales":    {k: v for k, v in CAUSALES.items()},
        "subcausales": SUBCAUSALES_FACTURACION,
        "canales":     CANALES,
        "servicios":   SERVICIOS,
        "tipos":       {k: v for k, v in TIPOS_PQR.items()},
    })


# ── Alias compatibilidad: exportar_sspd → exportar_sui ──────────────
@pqrs_bp.route("/exportar_sspd")
@login_requerido
def exportar_sspd():
    """Alias de compatibilidad para /pqrs/exportar_sui."""
    return exportar_sui()
