"""routes/dashboard.py — Panel principal con KPIs."""
from flask import Blueprint, render_template, session, redirect, url_for
from core.database_manager import get_db
from core.seguridad import login_requerido
from datetime import datetime, date

dash_bp = Blueprint("dashboard", __name__)


@dash_bp.route("/")
@dash_bp.route("/dashboard")
@login_requerido
def index():
    conn = get_db()
    hoy = date.today().isoformat()
    anio = datetime.now().year

    # KPIs generales
    total_docs  = conn.execute("SELECT COUNT(*) as c FROM registro_central").fetchone()["c"]
    docs_pend   = conn.execute("SELECT COUNT(*) as c FROM registro_central WHERE estado IN('Borrador','En_revision','En_autorizacion')").fetchone()["c"]
    total_subs  = conn.execute("SELECT COUNT(*) as c FROM contactos WHERE tipo_contacto='Suscriptor' AND activo_desactivo='ACTIVO'").fetchone()["c"]
    pqrs_pend   = conn.execute("SELECT COUNT(*) as c FROM pqrs WHERE estado_pqr IN('Recibida','En_tramite')").fetchone()["c"]
    pqrs_venc   = conn.execute("SELECT COUNT(*) as c FROM pqrs WHERE fecha_limite<? AND estado_pqr NOT IN('Respondida','Cerrada')",(hoy,)).fetchone()["c"]
    tareas_hoy  = conn.execute("SELECT COUNT(*) as c FROM tareas WHERE fecha_programada=? AND estado_tarea='Pendiente'",(hoy,)).fetchone()["c"]
    ots_activas = conn.execute("SELECT COUNT(*) as c FROM ordenes_trabajo WHERE estado_ot IN('Pendiente','En Ejecucion')").fetchone()["c"]
    fallas_act  = conn.execute("SELECT COUNT(*) as c FROM gis_reportes_fallas WHERE estado_reparacion='Pendiente'").fetchone()["c"]

    # Indicadores mes actual
    mes = datetime.now().month
    ind = conn.execute("SELECT ianc,produccion_m3,facturado_m3 FROM indicadores_mensuales WHERE anio=? AND mes=?",
                       (anio, mes)).fetchone()

    # Ultimos 5 documentos
    ultimos_docs = conn.execute("""
        SELECT codigo_completo, asunto_resumen, estado, fecha_radicacion
        FROM registro_central ORDER BY pk_registro_id DESC LIMIT 5
    """).fetchall()

    # Ultimas 5 PQRS
    ultimas_pqrs = conn.execute("""
        SELECT r.codigo_completo, c.razon_social, p.tipo_pqr, p.estado_pqr, p.fecha_limite
        FROM pqrs p
        JOIN registro_central r ON p.fk_registro_id=r.pk_registro_id
        JOIN contactos c ON p.fk_suscriptor_id=c.pk_contacto_id
        ORDER BY p.pk_pqr_id DESC LIMIT 5
    """).fetchall()

    # Acciones pendientes del usuario
    rol = session.get("rol")
    mis_acciones = []
    if rol in ("presidente","tesorera","secretaria"):
        firmante = conn.execute(
            "SELECT pk_firmante_id FROM firmantes WHERE cargo LIKE ? AND activo=1",
            (f"%{rol.capitalize()}%",)
        ).fetchone()
        if firmante:
            mis_acciones = conn.execute("""
                SELECT a.pk_accion_id, r.codigo_completo, r.asunto_resumen, a.fecha_limite, a.tipo_accion
                FROM acciones_pendientes a
                JOIN registro_central r ON a.fk_registro_id=r.pk_registro_id
                WHERE a.responsable_id=? AND a.estado='Pendiente'
                ORDER BY a.fecha_limite ASC LIMIT 5
            """, (firmante["pk_firmante_id"],)).fetchall()

    conn.close()
    return render_template("dashboard.html",
        total_docs=total_docs, docs_pend=docs_pend, total_subs=total_subs,
        pqrs_pend=pqrs_pend, pqrs_venc=pqrs_venc, tareas_hoy=tareas_hoy,
        ots_activas=ots_activas, fallas_act=fallas_act,
        indicador=ind, ultimos_docs=ultimos_docs, ultimas_pqrs=ultimas_pqrs,
        mis_acciones=mis_acciones, anio=anio, mes=mes)
