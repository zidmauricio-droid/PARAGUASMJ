"""
routes/emergencias.py — GA-08 Proyectos (PEC como tipo de proyecto)
LEGACY: em_bp redirige a /proyectos para mantener compatibilidad con URLs antiguas.
El Plan de Emergencias y Contingencias (PEC) NO es un módulo independiente.
Es un tipo de proyecto dentro de GA-08 Proyectos.
"""
from flask import Blueprint, redirect, url_for
from core.seguridad import login_requerido

em_bp = Blueprint("emergencias", __name__, url_prefix="/emergencias")


@em_bp.route("/", defaults={"path": ""})
@em_bp.route("/<path:path>")
@login_requerido
def redirigir_a_proyectos(path):
    return redirect(url_for("proyectos2.panel"), code=301)
