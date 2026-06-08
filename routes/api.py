"""
routes/api.py — API interna del sistema.
Mejoras del PROGRAMA.doc:
  - Firmantes dinámicos por documento (tabla documento_firmantes)
  - Historial de navegación (pushState via frontend)
  - Paginación de documentos (lazy loading)
"""
from flask import Blueprint, jsonify, request, session
from core.database_manager import get_db
from core.otp_manager import OTPManager
from core.seguridad import login_requerido
from core.capability_registry import CapabilityRegistry
from datetime import datetime

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ── OTP (sistema original mejorado) ────────────────────────────────
@api_bp.route("/otp/enviar", methods=["POST"])
@login_requerido
def otp_enviar():
    data = request.get_json()
    registro_id = data.get("registro_id")
    firmante_id = data.get("firmante_id")
    if not registro_id or not firmante_id:
        return jsonify({"ok": False, "error": "Faltan parámetros"}), 400
    mgr = OTPManager()
    return jsonify(mgr.iniciar_autorizacion(registro_id, firmante_id))


@api_bp.route("/otp/verificar", methods=["POST"])
def otp_verificar():
    data = request.get_json()
    registro_id = data.get("registro_id")
    firmante_id = data.get("firmante_id")
    codigo      = data.get("codigo")
    if not all([registro_id, firmante_id, codigo]):
        return jsonify({"ok": False, "error": "Faltan parámetros"}), 400
    mgr = OTPManager()
    return jsonify(mgr.verificar_otp(registro_id, firmante_id, codigo))


# ── Firmantes dinámicos por documento (PROGRAMA.doc) ───────────────
@api_bp.route("/documento/<int:doc_id>/firmantes")
@login_requerido
def obtener_firmantes(doc_id):
    """Retorna los firmantes asignados a un documento con su estado."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT df.id, f.nombre_completo, f.cargo, f.whatsapp,
                   df.orden_firma, df.estado, df.fecha_aprobacion
            FROM documento_firmantes df
            JOIN firmantes f ON df.firmante_id = f.pk_firmante_id
            WHERE df.documento_id = ?
            ORDER BY df.orden_firma
        """, (doc_id,)).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@api_bp.route("/documento/<int:doc_id>/firmantes/asignar", methods=["POST"])
@login_requerido
def asignar_firmantes(doc_id):
    """Asigna firmantes dinámicamente a un documento."""
    data = request.get_json()
    firmantes = data.get("firmantes", [])  # [{firmante_id, orden_firma}]
    if not firmantes:
        return jsonify({"ok": False, "error": "Sin firmantes"}), 400
    conn = get_db()
    try:
        # Limpiar asignaciones previas pendientes
        conn.execute("""
            DELETE FROM documento_firmantes
            WHERE documento_id=? AND estado='pendiente'
        """, (doc_id,))
        for f in firmantes:
            conn.execute("""
                INSERT INTO documento_firmantes
                (documento_id, firmante_id, orden_firma, estado)
                VALUES (?, ?, ?, 'pendiente')
            """, (doc_id, f["firmante_id"], f.get("orden_firma", 1)))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@api_bp.route("/documento/<int:doc_id>/validar_otp", methods=["POST"])
def validar_otp_documento(doc_id):
    """Valida OTP para firmante dinámico. PROGRAMA.doc patrón."""
    data       = request.get_json()
    firmante_id= data.get("firmante_id")
    codigo     = data.get("codigo", "").strip().upper()
    if not firmante_id or not codigo:
        return jsonify({"ok": False, "error": "Faltan datos"}), 400
    # Usa el OTPManager existente
    mgr = OTPManager()
    resultado = mgr.verificar_otp(doc_id, firmante_id, codigo)
    if resultado.get("ok"):
        # Actualizar tabla documento_firmantes
        conn = get_db()
        try:
            conn.execute("""
                UPDATE documento_firmantes
                SET estado='aprobado', fecha_aprobacion=?
                WHERE documento_id=? AND firmante_id=?
            """, (datetime.now().isoformat(), doc_id, firmante_id))
            # Verificar si todos aprobaron
            pendientes = conn.execute("""
                SELECT COUNT(*) as c FROM documento_firmantes
                WHERE documento_id=? AND estado='pendiente'
            """, (doc_id,)).fetchone()["c"]
            if pendientes == 0:
                conn.execute("""
                    UPDATE registro_central SET estado='Aprobado'
                    WHERE pk_registro_id=?
                """, (doc_id,))
            conn.commit()
        finally:
            conn.close()
    return jsonify(resultado)


# ── Buscar contactos ─────────────────────────────────────────────────
@api_bp.route("/contactos/buscar")
@login_requerido
def buscar_contactos():
    q    = request.args.get("q", "").strip()
    tipo = request.args.get("tipo", "")
    conn = get_db()
    sql  = "SELECT pk_contacto_id,codigo_interno,razon_social,tipo_contacto FROM contactos WHERE activo=1"
    params = []
    if q:
        sql += " AND (razon_social LIKE ? OR codigo_interno LIKE ?)"; params.extend([f"%{q}%"]*2)
    if tipo:
        sql += " AND tipo_contacto=?"; params.append(tipo)
    sql += " ORDER BY razon_social LIMIT 20"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ── Documentos paginados (lazy loading - PROGRAMA.doc) ──────────────
@api_bp.route("/documentos")
@login_requerido
def listar_documentos_api():
    """Endpoint paginado para evitar lentitud con muchos registros."""
    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    area     = request.args.get("area", "")
    estado   = request.args.get("estado", "")
    q        = request.args.get("q", "").strip()
    offset   = (page - 1) * per_page

    conn = get_db()
    try:
        sql    = """SELECT r.pk_registro_id, r.codigo_completo, r.asunto_resumen,
                           r.estado, r.fecha_radicacion, r.area, r.tipo_documento
                    FROM registro_central r WHERE 1=1"""
        params = []
        if area:
            sql += " AND r.area=?"; params.append(area)
        if estado:
            sql += " AND r.estado=?"; params.append(estado)
        if q:
            sql += " AND (r.codigo_completo LIKE ? OR r.asunto_resumen LIKE ?)"; params.extend([f"%{q}%"]*2)
        sql += f" ORDER BY r.pk_registro_id DESC LIMIT {per_page} OFFSET {offset}"
        rows = conn.execute(sql, params).fetchall()
        return jsonify({
            "items":    [dict(r) for r in rows],
            "has_more": len(rows) == per_page,
            "page":     page
        })
    finally:
        conn.close()


# ── KPIs del dashboard ───────────────────────────────────────────────
@api_bp.route("/dashboard/kpis")
@login_requerido
def dashboard_kpis():
    conn = get_db()
    from datetime import date
    hoy = date.today().isoformat()
    data = {
        "documentos_pendientes": conn.execute(
            "SELECT COUNT(*) as c FROM registro_central WHERE estado IN('Borrador','En_revision','En_autorizacion')"
        ).fetchone()["c"],
        "pqrs_activas": conn.execute(
            "SELECT COUNT(*) as c FROM pqrs WHERE estado_pqr IN('Recibida','En_tramite')"
        ).fetchone()["c"],
        "pqrs_vencidas": conn.execute(
            "SELECT COUNT(*) as c FROM pqrs WHERE fecha_limite<? AND estado_pqr NOT IN('Respondida','Cerrada')", (hoy,)
        ).fetchone()["c"],
        "fallas_pendientes": conn.execute(
            "SELECT COUNT(*) as c FROM gis_reportes_fallas WHERE estado_reparacion='Pendiente'"
        ).fetchone()["c"],
    }
    conn.close()
    return jsonify(data)


# ── Baseline RC5.5 — estado arquitectonico ──────────────────────────
@api_bp.route("/baseline/status")
@login_requerido
def baseline_status():
    """Estado del baseline RC5.5: perfil activo, capas, integridad."""
    return jsonify(CapabilityRegistry().get_baseline_info())


# ── Firmantes disponibles para asignar ──────────────────────────────
@api_bp.route("/firmantes")
@login_requerido
def listar_firmantes():
    conn = get_db()
    rows = conn.execute(
        "SELECT pk_firmante_id,nombre_completo,cargo,whatsapp FROM firmantes WHERE activo=1 ORDER BY nombre_completo"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
