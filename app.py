"""
app.py — PARAGUASMJ
Punto de entrada del servidor Flask. Compatible con PyInstaller.
"""
import os, sys, logging, atexit
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session

# Resolucion de rutas compatible con PyInstaller
def resolver_ruta(rel):
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel)

app = Flask(__name__,
    static_folder=resolver_ruta("static"),
    template_folder=resolver_ruta("templates"))

# Configuracion
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import Config
app.config.from_object(Config)

# Logging
from core.logger import configurar_logger
logger = configurar_logger("sigca")

# Blueprints
from routes.autenticacion  import auth_bp
from routes.dashboard      import dash_bp
from routes.documentos     import docs_bp
from routes.pqrs           import pqrs_bp
from routes.gis            import gis_bp
from routes.balance_hidrico import bh_bp
from routes.comunicaciones  import com_bp
from routes.proyectos       import proy_bp
from routes.api             import api_bp
from routes.finanzas        import fin_bp
from routes.reportes_normativos import rep_bp
from routes.auditoria        import aud_bp
from routes.proyectos_v2     import proy2_bp
from routes.emergencias      import em_bp
from routes.convenios        import conv_bp
from routes.carpetas_bp      import carpetas_bp
from routes.expedientes      import expedientes_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dash_bp)
app.register_blueprint(docs_bp)
app.register_blueprint(pqrs_bp)
app.register_blueprint(gis_bp)
app.register_blueprint(bh_bp)
app.register_blueprint(com_bp)
app.register_blueprint(proy_bp)
app.register_blueprint(api_bp)
app.register_blueprint(fin_bp)
app.register_blueprint(rep_bp)
app.register_blueprint(aud_bp)
app.register_blueprint(proy2_bp)
app.register_blueprint(em_bp)
app.register_blueprint(conv_bp)
app.register_blueprint(carpetas_bp)
app.register_blueprint(expedientes_bp)

# ── Filtros Jinja2 ──────────────────────────────────────────────────
from utils.helpers import formatear_moneda, truncar
app.jinja_env.filters["moneda"] = formatear_moneda
app.jinja_env.filters["truncar"] = truncar

# ── Procesador de contexto global ──────────────────────────────────
@app.context_processor
def inyectar_contexto():
    from datetime import date
    from utils.seguridad import generar_token_csrf
    return dict(
        hoy=date.today().isoformat(),
        anio_actual=date.today().year,
        version="2026.1",
        csrf_token=generar_token_csrf,
    )

# ── Manejadores de errores ──────────────────────────────────────────
@app.errorhandler(404)
def error_404(e):
    return render_template("error.html", codigo=404, mensaje="Pagina no encontrada"), 404

@app.errorhandler(403)
def error_403(e):
    return render_template("error.html", codigo=403, mensaje="Acceso denegado"), 403

@app.errorhandler(500)
def error_500(e):
    logger.error(f"Error 500: {e}")
    return render_template("error.html", codigo=500, mensaje="Error interno del servidor"), 500

# ── Rutas extra ────────────────────────────────────────────────────
@app.route("/configuracion", methods=["GET","POST"])
def configuracion():
    from core.database_manager import get_db
    from utils.seguridad import verificar_token_csrf
    if "usuario_id" not in session:
        return redirect(url_for("autenticacion.login"))
    conn = get_db()
    if request.method == "POST":
        # Verificación CSRF — protege cambios de configuración críticos
        if not verificar_token_csrf():
            flash("Token de seguridad inválido. Recargue la página.", "danger")
            return redirect(url_for("configuracion"))
        from core.crypto_simple import cifrar
        _CLAVES_CIFRADAS = {"email_password", "whatsapp_api_key", "smtp_password"}
        categoria = request.form.get("categoria")
        for clave, valor in request.form.items():
            if clave not in ("categoria", "csrf_token"):
                if clave in _CLAVES_CIFRADAS and valor:
                    valor = cifrar(valor)
                old = conn.execute("SELECT valor FROM configuracion WHERE clave=?",(clave,)).fetchone()
                if old and old["valor"] != valor:
                    conn.execute("UPDATE configuracion SET valor=?,fecha_actualizacion=datetime('now'),usuario_ultima_modificacion=? WHERE clave=?",
                                 (valor, session.get("nombre_usuario"), clave))
                    conn.execute("INSERT INTO configuracion_historial(clave,valor_anterior,valor_nuevo,usuario) VALUES(?,?,?,?)",
                                 (clave, old["valor"], valor, session.get("nombre_usuario")))
        conn.commit()
        flash("Configuracion guardada exitosamente.", "success")

    categorias_raw = conn.execute("SELECT DISTINCT categoria FROM configuracion ORDER BY orden,categoria").fetchall()
    categorias = []
    for cat_row in categorias_raw:
        cat = cat_row["categoria"]
        configs = conn.execute("SELECT * FROM configuracion WHERE categoria=? ORDER BY orden",(cat,)).fetchall()
        categorias.append({"categoria": cat, "configs": configs})
    conn.close()
    return render_template("configuracion.html", categorias=categorias)


@app.route("/panel_reportes")
def panel_reportes():
    if "usuario_id" not in session:
        return redirect(url_for("autenticacion.login"))
    return render_template("panel_reportes.html")


@app.route("/reportes/exportar/trimestral", methods=["POST"])
def exportar_excel_trimestral():
    if "usuario_id" not in session:
        return redirect(url_for("autenticacion.login"))
    from core.reportes_excel import ReporteExcelManager
    from flask import send_file
    from io import BytesIO
    anio = int(request.form.get("anio", 2026))
    trim = int(request.form.get("trimestre", 2))
    try:
        mgr = ReporteExcelManager()
        wb  = mgr.generar_reporte_trimestral(anio, trim)
        buf = BytesIO()
        wb.save(buf); buf.seek(0)
        return send_file(buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"SIGCA_Reporte_T{trim}_{anio}.xlsx")
    except Exception as e:
        flash(f"Error al generar reporte: {e}", "danger")
        return redirect(url_for("panel_reportes"))


@app.route("/gestion_usuarios")
def gestion_usuarios():
    from core.seguridad import rol_requerido
    if session.get("rol") != "admin":
        flash("Solo el administrador puede gestionar usuarios.", "danger")
        return redirect(url_for("dashboard.index"))
    from core.database_manager import get_db
    conn = get_db()
    usuarios = conn.execute("SELECT pk_usuario_id,nombre_completo,nombre_usuario,rol,activo,ultimo_acceso FROM usuarios ORDER BY nombre_completo").fetchall()
    conn.close()
    return render_template("gestion_usuarios.html", usuarios=usuarios)


@app.route("/backup/crear", methods=["POST"])
def crear_backup_manual():
    """POST + CSRF — previene activación por GET externo (imágenes, iframes)."""
    from utils.seguridad import verificar_token_csrf
    if "usuario_id" not in session:
        return redirect(url_for("autenticacion.login"))
    if not verificar_token_csrf():
        flash("Token de seguridad inválido.", "danger")
        return redirect(url_for("dashboard.index"))
    from core.backup_manager import crear_backup
    ruta = crear_backup()
    if ruta:
        flash(f"Backup creado: {os.path.basename(ruta)}", "success")
    else:
        flash("Error al crear backup.", "danger")
    return redirect(url_for("dashboard.index"))


# ── WAL checkpoint periódico (#16) ────────────────────────────────
def _wal_checkpoint():
    """PRAGMA wal_checkpoint(TRUNCATE) — previene crecimiento indefinido del WAL."""
    try:
        from core.database_manager import get_db
        conn = get_db()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        logger.info("WAL checkpoint ejecutado")
    except Exception as e:
        logger.warning(f"WAL checkpoint falló: {e}")


# ── Scheduler APScheduler ──────────────────────────────────────────
def iniciar_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from core.scheduler_notificaciones import tarea_diaria_completa
        sched = BackgroundScheduler(daemon=True)
        sched.add_job(tarea_diaria_completa, "cron",
                      hour=Config.SCHEDULER_HORA, minute=Config.SCHEDULER_MINUTO)
        # WAL checkpoint cada 6 horas para mantener BD compacta (#16)
        sched.add_job(_wal_checkpoint, "interval", hours=6, id="wal_checkpoint")
        sched.start()
        atexit.register(lambda: sched.shutdown(wait=False))
        logger.info("Scheduler iniciado: tareas diarias a las %d:%02d",
                    Config.SCHEDULER_HORA, Config.SCHEDULER_MINUTO)
    except ImportError:
        logger.warning("APScheduler no instalado. Notificaciones automaticas desactivadas.")
    except Exception as e:
        logger.error(f"Error iniciando scheduler: {e}")


# ── Inicializacion ─────────────────────────────────────────────────
def inicializar_app():
    """Crea tablas si no existen y usuario admin inicial."""
    try:
        from database.inicializar_db import inicializar_base_datos, inicializar_tablas_extra
        inicializar_base_datos()
        inicializar_tablas_extra()
        from database.inicializar_db import inicializar_tablas_prog3_prog4
        inicializar_tablas_prog3_prog4()
    except Exception as e:
        logger.error(f"Error inicializando DB: {e}")

    # Ejecutar migraciones idempotentes en orden (017-020)
    _run_migrations()


def _run_migrations():
    """Corre migraciones pendientes al arranque. Cada una es idempotente."""
    from config import Config
    db = Config.DB_PATH
    migraciones = [
        "database.migrations.017_pqrs_sspd_campos",
        "database.migrations.018_pqrs_causales_sspd",
        "database.migrations.019_indices_rendimiento",
        "database.migrations.020_proyectos_periodo_flexible",
        "database.migrations.021_tipos_proyecto_e_indices",
    ]
    for mod_name in migraciones:
        try:
            import importlib
            mod = importlib.import_module(mod_name)
            mod.migrar(db)
        except Exception as e:
            logger.warning(f"Migración {mod_name}: {e}")


# Inicializar siempre al cargar el módulo (gunicorn, waitress o __main__)
inicializar_app()
iniciar_scheduler()

if __name__ == "__main__":
    logger.info("Iniciando PARAGUASMJ en http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
