"""
routes/reportes_normativos.py
Panel de reportes oficiales: FC15 IUS, Balance CAR, PUEAA, Actas.
Fuente: PROGRAMA_1.doc - todos los entregables normativos.
"""
from flask import Blueprint, render_template, request, send_file, redirect, url_for, flash, session
from core.reportes_sspd import ReportesSSPD
from core.indicadores_ius import calcular_ius_anual
from core.pdf_profesional import generar_pdf_documento, generar_acta_entrega_materiales
from core.email_manager import enviar_pueaa_car
from core.seguridad import login_requerido
from core.backup_manager import crear_backup
from datetime import datetime
from io import BytesIO
import os

rep_bp = Blueprint("reportes_normativos", __name__, url_prefix="/reportes")
_mgr = ReportesSSPD()


@rep_bp.route("/panel")
@login_requerido
def panel():
    anio_actual = datetime.now().year
    # Calcular IUS del año para mostrar en el panel
    ius = calcular_ius_anual(anio_actual)
    return render_template("reportes_normativos/panel.html",
                            anio=anio_actual, ius=ius)


@rep_bp.route("/ius/calcular/<int:anio>")
@login_requerido
def calcular_ius(anio):
    """API: retorna todos los indicadores IUS en JSON."""
    from flask import jsonify
    return jsonify(calcular_ius_anual(anio))


@rep_bp.route("/fc15/descargar", methods=["POST"])
@login_requerido
def descargar_fc15():
    """FC15 para XBRL Express de la SSPD."""
    anio = int(request.form.get("anio", datetime.now().year))
    try:
        wb  = _mgr.generar_fc15_ius(anio)
        buf = BytesIO(); wb.save(buf); buf.seek(0)
        return send_file(buf, as_attachment=True,
                         download_name=f"FC15_IUS_SIGCA_{anio}.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        flash(f"Error generando FC15: {e}", "danger")
        return redirect(url_for("reportes_normativos.panel"))


@rep_bp.route("/hoja_ius/descargar", methods=["POST"])
@login_requerido
def descargar_hoja_ius():
    """Hoja IUS completa estilo INFORMACION IUS 2024.xlsx."""
    anio = int(request.form.get("anio", datetime.now().year))
    try:
        wb  = _mgr.generar_hoja_ius_excel(anio)
        buf = BytesIO(); wb.save(buf); buf.seek(0)
        return send_file(buf, as_attachment=True,
                         download_name=f"INFORMACION_IUS_SIGCA_{anio}.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for("reportes_normativos.panel"))


@rep_bp.route("/balance_car/descargar", methods=["POST"])
@login_requerido
def descargar_balance_car():
    """Balance hídrico trimestral para CAR/PUEAA."""
    anio  = int(request.form.get("anio", datetime.now().year))
    trim  = int(request.form.get("trimestre", 1))
    try:
        wb  = _mgr.generar_balance_hidrico_car(anio, trim)
        buf = BytesIO(); wb.save(buf); buf.seek(0)
        return send_file(buf, as_attachment=True,
                         download_name=f"BalanceHidrico_CAR_T{trim}_{anio}.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for("reportes_normativos.panel"))


@rep_bp.route("/trimestral/descargar", methods=["POST"])
@login_requerido
def descargar_trimestral():
    """Reporte trimestral CAR/SSPD (3 hojas: Balance, Fallas, PQRS)."""
    from core.reportes_excel import ReporteExcelManager
    anio = int(request.form.get("anio", datetime.now().year))
    trim = int(request.form.get("trimestre", 2))
    try:
        mgr = ReporteExcelManager()
        wb  = mgr.generar_reporte_trimestral(anio, trim)
        buf = BytesIO(); wb.save(buf); buf.seek(0)
        return send_file(buf, as_attachment=True,
                         download_name=f"SIGCA_Reporte_T{trim}_{anio}.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for("reportes_normativos.panel"))


@rep_bp.route("/pueaa/enviar_car", methods=["POST"])
@login_requerido
def enviar_pueaa():
    """Envía el PUEAA (PDF) a la CAR por correo."""
    correo_car = request.form.get("correo_car", "sau@car.gov.co")
    pdf_path   = request.form.get("pdf_path","")
    ok = enviar_pueaa_car(pdf_path, correo_car)
    if ok:
        flash(f"PUEAA enviado exitosamente a {correo_car}", "success")
    else:
        flash("Error al enviar. Verifique la configuración SMTP en Configuración → Notificaciones.", "danger")
    return redirect(url_for("reportes_normativos.panel"))


@rep_bp.route("/acta_materiales/<int:oc_id>")
@login_requerido
def acta_materiales(oc_id):
    """Genera y descarga acta de entrega de materiales de una OC."""
    pdf_path = generar_acta_entrega_materiales(oc_id)
    if not pdf_path:
        flash("Error al generar acta.", "danger")
        return redirect(url_for("documentos.listar"))
    return send_file(pdf_path, as_attachment=True,
                     download_name=os.path.basename(pdf_path))


@rep_bp.route("/backup")
@login_requerido
def hacer_backup():
    ruta = crear_backup()
    if ruta:
        flash(f"Backup creado: {os.path.basename(ruta)}", "success")
    else:
        flash("Error al crear backup.", "danger")
    return redirect(url_for("reportes_normativos.panel"))
