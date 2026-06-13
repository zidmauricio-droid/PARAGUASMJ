"""
PARAGUASMJ — Módulo GE-01 Gobierno Corporativo
Gestión de Actas de Junta y Resoluciones/Acuerdos
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from core.database_manager import get_db
from core.seguridad import login_requerido
from utils.seguridad import verificar_token_csrf
import logging

gobierno_bp = Blueprint("gobierno", __name__, url_prefix="/ge")
logger = logging.getLogger("paraguasmj")


@gobierno_bp.route("/")
@login_requerido
def panel():
    conn = get_db()
    try:
        actas = conn.execute(
            "SELECT * FROM ge_actas ORDER BY anio DESC, numero DESC"
        ).fetchall()
        resoluciones = conn.execute(
            "SELECT * FROM ge_resoluciones ORDER BY anio DESC, numero DESC"
        ).fetchall()
    finally:
        conn.close()
    return render_template("ge/panel.html", actas=actas, resoluciones=resoluciones)


@gobierno_bp.route("/actas/nueva", methods=["POST"])
@login_requerido
def acta_nueva():
    verificar_token_csrf(request.form.get("csrf_token"))
    tipo        = request.form.get("tipo", "").strip()
    numero      = request.form.get("numero", "").strip()
    anio        = request.form.get("anio", "").strip()
    fecha       = request.form.get("fecha", "").strip()
    descripcion = request.form.get("descripcion", "").strip()

    if not all([tipo, numero, anio, fecha]):
        flash("Todos los campos obligatorios deben completarse.", "warning")
        return redirect(url_for("gobierno.panel"))

    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO ge_actas (tipo, numero, anio, fecha, descripcion, estado)
               VALUES (?, ?, ?, ?, ?, 'vigente')""",
            (tipo, numero, anio, fecha, descripcion)
        )
        conn.commit()
        flash("Acta registrada correctamente.", "success")
    except Exception as exc:
        logger.error("Error al insertar acta: %s", exc)
        flash("Error al guardar el acta.", "danger")
    finally:
        conn.close()
    return redirect(url_for("gobierno.panel"))


@gobierno_bp.route("/actas/<int:pk>/estado", methods=["POST"])
@login_requerido
def acta_estado(pk):
    verificar_token_csrf(request.form.get("csrf_token"))
    estado = request.form.get("estado", "").strip()
    if estado not in ("vigente", "derogada", "suspendida"):
        flash("Estado no válido.", "warning")
        return redirect(url_for("gobierno.panel"))

    conn = get_db()
    try:
        conn.execute(
            "UPDATE ge_actas SET estado=? WHERE pk_acta_id=?", (estado, pk)
        )
        conn.commit()
        flash("Estado del acta actualizado.", "success")
    except Exception as exc:
        logger.error("Error al actualizar estado de acta %s: %s", pk, exc)
        flash("Error al actualizar el estado.", "danger")
    finally:
        conn.close()
    return redirect(url_for("gobierno.panel"))


@gobierno_bp.route("/resoluciones/nueva", methods=["POST"])
@login_requerido
def resolucion_nueva():
    verificar_token_csrf(request.form.get("csrf_token"))
    numero           = request.form.get("numero", "").strip()
    anio             = request.form.get("anio", "").strip()
    fecha            = request.form.get("fecha", "").strip()
    asunto           = request.form.get("asunto", "").strip()
    texto_resolucion = request.form.get("texto_resolucion", "").strip()

    if not all([numero, anio, fecha, asunto]):
        flash("Todos los campos obligatorios deben completarse.", "warning")
        return redirect(url_for("gobierno.panel"))

    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO ge_resoluciones (numero, anio, fecha, asunto, texto_resolucion, estado)
               VALUES (?, ?, ?, ?, ?, 'vigente')""",
            (numero, anio, fecha, asunto, texto_resolucion)
        )
        conn.commit()
        flash("Resolución registrada correctamente.", "success")
    except Exception as exc:
        logger.error("Error al insertar resolución: %s", exc)
        flash("Error al guardar la resolución.", "danger")
    finally:
        conn.close()
    return redirect(url_for("gobierno.panel"))


@gobierno_bp.route("/resoluciones/<int:pk>/estado", methods=["POST"])
@login_requerido
def resolucion_estado(pk):
    verificar_token_csrf(request.form.get("csrf_token"))
    estado = request.form.get("estado", "").strip()
    if estado not in ("vigente", "derogada", "suspendida"):
        flash("Estado no válido.", "warning")
        return redirect(url_for("gobierno.panel"))

    conn = get_db()
    try:
        conn.execute(
            "UPDATE ge_resoluciones SET estado=? WHERE pk_res_id=?", (estado, pk)
        )
        conn.commit()
        flash("Estado de la resolución actualizado.", "success")
    except Exception as exc:
        logger.error("Error al actualizar estado de resolución %s: %s", pk, exc)
        flash("Error al actualizar el estado.", "danger")
    finally:
        conn.close()
    return redirect(url_for("gobierno.panel"))
