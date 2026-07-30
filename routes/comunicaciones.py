"""routes/comunicaciones.py — Comunicaciones recibidas."""
import logging as _logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from core.database_manager import get_db
from core.seguridad import login_requerido
from datetime import date, timedelta
_log_com = _logging.getLogger("sigca.comunicaciones")

com_bp = Blueprint("comunicaciones", __name__, url_prefix="/comunicaciones")


@com_bp.route("/")
@login_requerido
def listar():
    estado = request.args.get("estado","")
    conn   = get_db()
    sql    = "SELECT * FROM comunicaciones_recibidas WHERE 1=1"
    params = []
    if estado:
        sql += " AND estado=?"; params.append(estado)
    sql += " ORDER BY fecha_recepcion DESC"
    coms   = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template("comunicaciones/lista.html", comunicaciones=coms, estado_sel=estado)


@com_bp.route("/nueva", methods=["GET","POST"])
@login_requerido
def nueva():
    if request.method == "POST":
        entidad = request.form["entidad_remitente"].strip()
        asunto  = request.form["asunto"].strip()
        fecha_r = request.form.get("fecha_recepcion") or date.today().isoformat()
        req_resp= 1 if request.form.get("requiere_respuesta") else 0
        dias_pl = int(request.form.get("dias_plazo",15))
        fecha_l = (date.fromisoformat(fecha_r) + timedelta(days=dias_pl)).isoformat() if req_resp else None
        obs     = request.form.get("observaciones","")
        radicado= request.form.get("radicado_externo","")
        conn    = get_db()
        try:
            conn.execute("""
                INSERT INTO comunicaciones_recibidas(entidad_remitente,radicado_externo,asunto,
                fecha_recepcion,requiere_respuesta,fecha_limite_resp,estado,observaciones)
                VALUES(?,?,?,?,?,?,'Pendiente',?)
            """,(entidad,radicado,asunto,fecha_r,req_resp,fecha_l,obs))
            conn.commit()
            flash("Comunicacion registrada.", "success")
            return redirect(url_for("comunicaciones.listar"))
        except Exception as e:
            conn.rollback()
            _log_com.error("nueva comunicacion: %s", e, exc_info=True)
            flash("Error al registrar la comunicación. Contacte al administrador.", "danger")
        finally:
            conn.close()
    return render_template("comunicaciones/nueva.html", hoy=date.today().isoformat())
