"""
routes/documentos.py — CRUD completo de documentos institucionales.
Mejoras del documento del editor:
  - API guardado borrador (autosave cada 30s)
  - API firmantes activos para insercion en editor
  - API representante legal desde config
  - Upload de imagenes para el editor
  - Historial de versiones del contenido
  - Exportar a DOCX
  - Plantillas predefinidas (oficio, acta, contestacion fiscal)
  - Estadisticas de documentos
  - Vista previa en linea del PDF
"""
import re, os, json
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, send_file, abort, jsonify)
from werkzeug.utils import secure_filename
from core.database_manager import get_db, obtener_consecutivo, registrar_log
from core.seguridad import login_requerido
from core.auditoria import auditar
from datetime import datetime, timedelta, date

docs_bp = Blueprint("documentos", __name__, url_prefix="/documentos")

AREAS = [("GA","Gestion Ambiental"),("GC","Gestion Comercial"),
         ("GF","Gestion Financiera"),("GE","Gestion Estrategica"),
         ("GL","Gestion Legal")]
TIPOS = [
    ("OFI","Oficio"),("ACT","Acta"),("RES","Resolución"),
    ("INF","Informe"),("OT","Orden de Trabajo"),("OC","Orden de Compra"),
    ("PQR","PQRS"),("CON","Convenio / Contrato"),("COT","Cotización"),
    ("CIR","Circular"),("REQ","Contestación Requerimiento Fiscal"),
    ("ASEXR","Asistencia Extrapresupuestaria Rodamiento"),
    ("CCB","Cuenta de Cobro"),("CDP","Disponibilidad Presupuestal"),
    ("CER","Certificado"),("CL","Certificado de Libertad"),
    ("CONV","Convocatoria"),("CRP","Certificado de Registro Presupuestal"),
    ("CUU","Contrato Condiciones Uniformes"),("ESF","Estados Financieros"),
    ("EVA","Evaluación de Desempeño"),("FM","Formato / Plantilla"),
    ("FOR","Formulario"),("HV","Hoja de Vida"),
    ("IND","Indicador de Gestión"),("INV","Inventario"),
    ("LIC","Licencia / Permiso"),("LMCRO","Lectura Macromedidor"),
    ("MAN","Manual"),("MEM","Memorando"),
    ("MIC","Lectura Micromedidor"),("PLA","Plan"),
    ("POL","Política"),("PRE","Presupuesto"),
    ("RAL","Respuesta a Alcaldía"),("RCAR","Respuesta a CAR"),
    ("RIE","Matriz de Riesgos"),("RP","Registro Presupuestal"),
    ("RSSPD","Respuesta / Reporte a SSPD"),("SOL","Solicitud Individual"),
    ("EST","Estudio"),("ACP","Acuerdo de Pago"),("MEM","Memorando"),
    ("P","Procedimiento"),
]

# Extensiones de imagen permitidas en el editor
IMG_EXTS = {"png","jpg","jpeg","gif","webp","svg"}

# ── Plantillas predefinidas institucionales ─────────────────────────
PLANTILLAS = {
    "oficio_car": {
        "nombre": "Oficio a la CAR",
        "html": """<p><strong>Señores</strong><br>
CORPORACIÓN AUTÓNOMA REGIONAL DE CUNDINAMARCA - CAR<br>
Oficina Regional Gualivá<br>
Ciudad</p>
<p>Asunto: [ASUNTO]</p>
<p>Respetados señores:</p>
<p>Por medio del presente, la Asociación de Suscriptores del Acueducto Comunitario
El Puente – ASUACAP, identificada con NIT 832.001.389-2, con domicilio en el
Caserío El Puente, Villeta, Cundinamarca, se permite [ACCION].</p>
<p>Para mayor información, quedamos atentos en nuestras oficinas ubicadas en
el Caserío El Puente, Villeta, Cundinamarca, o al correo
aacueductoelpuente@yahoo.com</p>
<p>Cordialmente,</p>"""
    },
    "acta_reunion": {
        "nombre": "Acta de Reunión",
        "html": """<h2>ACTA DE REUNIÓN</h2>
<table border="1" cellpadding="8" style="width:100%;border-collapse:collapse;">
  <tr><td><strong>Fecha:</strong></td><td>[FECHA]</td><td><strong>Hora inicio:</strong></td><td></td></tr>
  <tr><td><strong>Lugar:</strong></td><td colspan="3">Sede ASUACAP — Caserío El Puente, Villeta</td></tr>
  <tr><td><strong>Convocatoria:</strong></td><td colspan="3">Junta Directiva ASUACAP</td></tr>
</table>
<h3>1. Asistentes</h3>
<table border="1" cellpadding="6" style="width:100%;border-collapse:collapse;">
  <tr><th>Nombre</th><th>Cargo</th><th>Firma</th></tr>
  <tr><td></td><td></td><td></td></tr>
</table>
<h3>2. Orden del Día</h3>
<ol><li></li><li></li><li></li></ol>
<h3>3. Desarrollo de la Reunión</h3>
<p></p>
<h3>4. Compromisos y Responsables</h3>
<table border="1" cellpadding="6" style="width:100%;border-collapse:collapse;">
  <tr><th>Compromiso</th><th>Responsable</th><th>Fecha límite</th></tr>
  <tr><td></td><td></td><td></td></tr>
</table>
<h3>5. Cierre</h3>
<p>No habiendo más asuntos que tratar, se levanta la sesión a las ___ horas.</p>"""
    },
    "contestacion_fiscal": {
        "nombre": "Contestación Requerimiento Fiscal",
        "html": """<h2>CONTESTACIÓN A REQUERIMIENTO FISCAL</h2>
<table border="1" cellpadding="8" style="width:100%;border-collapse:collapse;">
  <tr><td><strong>Radicado requerimiento:</strong></td><td></td></tr>
  <tr><td><strong>Entidad requirente:</strong></td><td></td></tr>
  <tr><td><strong>Fecha notificación:</strong></td><td></td></tr>
  <tr><td><strong>Valor cuestionado:</strong></td><td></td></tr>
</table>
<h3>I. POSICIÓN JURÍDICA</h3>
<p>La Asociación ASUACAP, actuando de buena fe y en ejercicio del derecho de defensa
consagrado en el artículo 29 de la Constitución Política de Colombia, se permite
manifestar su posición frente a los hechos imputados:</p>
<h3>II. DESCRIPCIÓN DE LOS HECHOS</h3>
<h4>EJE 1:</h4>
<table border="1" cellpadding="6" style="width:100%;border-collapse:collapse;">
  <tr><th>Tiempo</th><th>Modo</th><th>Lugar</th><th>Valor</th><th>Responsable</th></tr>
  <tr><td></td><td></td><td></td><td></td><td></td></tr>
</table>
<h3>III. SOLICITUDES</h3>
<ol><li>Declarar exonerada a ASUACAP de la responsabilidad fiscal imputada.</li>
    <li>[OTRAS SOLICITUDES]</li></ol>"""
    },
    "acta_entrega_materiales": {
        "nombre": "Acta Entrega de Materiales",
        "html": """<h2>ACTA DE ENTREGA DE MATERIALES</h2>
<table border="1" cellpadding="8" style="width:100%;border-collapse:collapse;">
  <tr><td><strong>Orden de Compra:</strong></td><td></td><td><strong>Fecha:</strong></td><td></td></tr>
  <tr><td><strong>Proveedor:</strong></td><td colspan="3"></td></tr>
</table>
<h3>Relación de Materiales Entregados</h3>
<table border="1" cellpadding="6" style="width:100%;border-collapse:collapse;">
  <tr><th>N°</th><th>Descripción</th><th>Unidad</th><th>Cantidad</th><th>Precio Unit.</th><th>Total</th></tr>
  <tr><td>1</td><td></td><td></td><td></td><td></td><td></td></tr>
  <tr><td colspan="5"><strong>TOTAL</strong></td><td></td></tr>
</table>
<p>La persona que suscribe declara recibir a satisfacción los materiales relacionados.</p>"""
    },
    "oficio_sspd": {
        "nombre": "Oficio a la SSPD",
        "html": """<p><strong>Señores</strong><br>
SUPERINTENDENCIA DE SERVICIOS PÚBLICOS DOMICILIARIOS - SSPD<br>
Bogotá D.C.</p>
<p>Asunto: Remisión de información SUI — Año [AÑO]</p>
<p>Respetados señores:</p>
<p>ASUACAP, prestador de los servicios de acueducto y alcantarillado con código SUI
[CODIGO_SUI], da cumplimiento a la obligación de reporte periódico de información
al Sistema Único de Información, en los términos del artículo 14 de la Ley 142 de
1994 y la Resolución SSPD [RESOLUCION].</p>
<p>Se adjuntan los formularios FC01, FC03 y FC15 debidamente diligenciados.</p>"""
    }
}


# ── Listar documentos ────────────────────────────────────────────────
@docs_bp.route("/")
@login_requerido
def listar():
    area     = request.args.get("area","")
    estado   = request.args.get("estado","")
    q        = request.args.get("q","").strip()
    tipo     = request.args.get("tipo","")
    pagina   = request.args.get("pagina",1,type=int)
    por_pag  = 20

    conn = get_db()
    sql  = """SELECT r.*, c.razon_social as contacto_nombre
              FROM registro_central r
              LEFT JOIN contactos c ON r.fk_contacto_id=c.pk_contacto_id
              WHERE 1=1"""
    p = []
    if area:   sql += " AND r.area=?";           p.append(area)
    if estado: sql += " AND r.estado=?";          p.append(estado)
    if tipo:   sql += " AND r.tipo_documento=?";  p.append(tipo)
    if q:
        sql += " AND (r.codigo_completo LIKE ? OR r.asunto_resumen LIKE ? OR c.razon_social LIKE ?)"
        p.extend([f"%{q}%"]*3)

    total     = conn.execute(f"SELECT COUNT(*) as c FROM ({sql})", p).fetchone()["c"]
    sql      += f" ORDER BY r.pk_registro_id DESC LIMIT {por_pag} OFFSET {(pagina-1)*por_pag}"
    docs      = conn.execute(sql, p).fetchall()
    stats     = conn.execute("""
        SELECT estado, COUNT(*) as c FROM registro_central
        GROUP BY estado ORDER BY c DESC
    """).fetchall()
    conn.close()

    return render_template("documentos/lista.html", documentos=docs,
        areas=AREAS, tipos=TIPOS,
        area_sel=area, estado_sel=estado, tipo_sel=tipo, q=q,
        pagina=pagina, total_pags=(total+por_pag-1)//por_pag,
        total=total, stats=stats)


# ── Nuevo documento (con editor TipTap) ─────────────────────────────
@docs_bp.route("/nuevo", methods=["GET","POST"])
@login_requerido
def nuevo():
    conn = get_db()

    if request.method == "POST":
        area        = request.form.get("area","GA")
        tipo        = request.form.get("tipo_documento","OFI")
        anio        = datetime.now().year
        asunto      = (request.form.get("asunto_resumen") or "Sin título").strip()
        fecha_rad   = request.form.get("fecha_radicacion") or date.today().isoformat()
        fk_contacto = request.form.get("fk_contacto_id") or None
        notas       = request.form.get("notas_internas","")
        # Validar área
        areas_ok = ('GA','GC','GF','GE','GL')
        if area not in areas_ok:
            area = 'GA'
        contenido   = request.form.get("contenido_html","")
        fecha_venc  = request.form.get("fecha_vencimiento") or None
        # Firmantes seleccionados manualmente en el editor
        firmantes_sel = request.form.getlist("firmantes_sel")

        try:
            consec  = obtener_consecutivo(area, tipo, anio)
            codigo  = f"{area}-{tipo}-{anio}-{consec:03d}"
            fecha_r = datetime.strptime(fecha_rad, "%Y-%m-%d")
            cfg_row = conn.execute("SELECT clave,valor FROM configuracion WHERE clave IN ('dias_alerta_documentos','dias_plazo_autorizacion')").fetchall()
            cfg     = {r["clave"]: int(r["valor"]) for r in cfg_row}
            dias_al = cfg.get("dias_alerta_documentos", 4)
            dias_pl = cfg.get("dias_plazo_autorizacion", 7)

            conn.execute("""
                INSERT INTO registro_central
                (codigo_completo,area,tipo_documento,anio,consecutivo,fecha_radicacion,
                 fecha_vencimiento,fk_contacto_id,asunto_resumen,notas_internas,estado,creado_por)
                VALUES(?,?,?,?,?,?,?,?,?,?,'Borrador',?)
            """,(codigo,area,tipo,anio,consec,fecha_rad,fecha_venc,fk_contacto,asunto,notas,
                 session.get("nombre_usuario")))
            reg_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]

            # Guardar contenido del editor
            plain = re.sub(r"<[^<]+?>","",contenido)
            conn.execute("""
                INSERT INTO contenido_documento
                (fk_registro_id,contenido_html,contenido_plain,editado_por)
                VALUES(?,?,?,?)
            """,(reg_id, contenido, plain, session.get("nombre_usuario")))

            # Plazos de notificacion
            conn.execute("""
                INSERT INTO plazos_documento(fk_registro_id,fecha_inicio_notificaciones)
                VALUES(?,?)
            """,(reg_id, (fecha_r+timedelta(days=dias_al)).date().isoformat()))

            fl_accion = (fecha_r+timedelta(days=dias_pl)).date().isoformat()

            # Firmantes: usar seleccion del editor si hay, sino reglas por tipo
            if firmantes_sel:
                for i, fid in enumerate(firmantes_sel, 1):
                    conn.execute("""
                        INSERT INTO documento_firmantes(documento_id,firmante_id,orden_firma,estado)
                        VALUES(?,?,?,'pendiente')
                    """,(reg_id, int(fid), i))
                    conn.execute("""
                        INSERT INTO acciones_pendientes(fk_registro_id,tipo_accion,responsable_id,fecha_limite)
                        VALUES(?,'autorizar',?,?)
                    """,(reg_id, int(fid), fl_accion))
            else:
                reglas = conn.execute("""
                    SELECT pk_firmante_id FROM reglas_firmantes
                    WHERE tipo_documento=? AND obligatorio=1 ORDER BY orden_firma
                """,(tipo,)).fetchall()
                for i, r2 in enumerate(reglas, 1):
                    conn.execute("""
                        INSERT INTO documento_firmantes(documento_id,firmante_id,orden_firma,estado)
                        VALUES(?,?,?,'pendiente')
                    """,(reg_id, r2["pk_firmante_id"], i))
                    conn.execute("""
                        INSERT INTO acciones_pendientes(fk_registro_id,tipo_accion,responsable_id,fecha_limite)
                        VALUES(?,'autorizar',?,?)
                    """,(reg_id, r2["pk_firmante_id"], fl_accion))

            conn.execute("""
                INSERT INTO seguimiento_documento
                (fk_registro_id,estado_actual,fecha_cambio,usuario,observaciones)
                VALUES(?,'Borrador',CURRENT_TIMESTAMP,?,'Documento creado desde editor')
            """,(reg_id, session.get("nombre_usuario")))

            conn.commit()
            auditar(f"Documento creado: {codigo}", modulo="documentos")
            flash(f"✅ Documento {codigo} creado exitosamente.", "success")
            return redirect(url_for("documentos.ver", registro_id=reg_id))

        except Exception as e:
            conn.rollback()
            flash(f"Error al crear documento: {e}", "danger")

    contactos  = conn.execute(
        "SELECT pk_contacto_id,razon_social FROM contactos WHERE activo=1 ORDER BY razon_social"
    ).fetchall()
    firmantes  = conn.execute(
        "SELECT pk_firmante_id,nombre_completo,cargo FROM firmantes WHERE activo=1 ORDER BY nombre_completo"
    ).fetchall()
    conn.close()

    return render_template("documentos/nuevo.html",
        areas=AREAS, tipos=TIPOS, contactos=contactos,
        firmantes=firmantes, plantillas=PLANTILLAS,
        hoy=date.today().isoformat())


# ── Ver documento ────────────────────────────────────────────────────
@docs_bp.route("/<int:registro_id>")
@login_requerido
def ver(registro_id):
    conn = get_db()
    doc = conn.execute("""
        SELECT r.*, c.razon_social as contacto_nombre
        FROM registro_central r
        LEFT JOIN contactos c ON r.fk_contacto_id=c.pk_contacto_id
        WHERE r.pk_registro_id=?
    """,(registro_id,)).fetchone()
    if not doc:
        abort(404)

    contenido = conn.execute(
        "SELECT contenido_html,version,fecha_edicion FROM contenido_documento WHERE fk_registro_id=?",
        (registro_id,)
    ).fetchone()
    adjuntos   = conn.execute("SELECT * FROM documentos_adjuntos WHERE fk_registro_id=?",(registro_id,)).fetchall()
    seguim     = conn.execute("SELECT * FROM seguimiento_documento WHERE fk_registro_id=? ORDER BY fecha_cambio DESC",(registro_id,)).fetchall()
    acciones   = conn.execute("""
        SELECT a.*, f.nombre_completo, f.cargo
        FROM acciones_pendientes a
        JOIN firmantes f ON a.responsable_id=f.pk_firmante_id
        WHERE a.fk_registro_id=? ORDER BY a.fecha_limite
    """,(registro_id,)).fetchall()
    otps       = conn.execute("""
        SELECT o.*, f.nombre_completo, f.cargo
        FROM autorizaciones_otp o
        JOIN firmantes f ON o.fk_firmante_id=f.pk_firmante_id
        WHERE o.fk_registro_id=? ORDER BY o.fecha_envio DESC
    """,(registro_id,)).fetchall()
    firmantes_doc = conn.execute("""
        SELECT df.*, f.nombre_completo, f.cargo, f.whatsapp
        FROM documento_firmantes df
        JOIN firmantes f ON df.firmante_id=f.pk_firmante_id
        WHERE df.documento_id=? ORDER BY df.orden_firma
    """,(registro_id,)).fetchall()
    conn.close()

    return render_template("documentos/ver.html", doc=doc,
        contenido=contenido, adjuntos=adjuntos, seguimiento=seguim,
        acciones=acciones, otps=otps, firmantes_doc=firmantes_doc,
        areas=AREAS, tipos=TIPOS)


# ── Editar contenido de un documento existente ──────────────────────
@docs_bp.route("/<int:registro_id>/editar", methods=["GET","POST"])
@login_requerido
def editar(registro_id):
    conn = get_db()
    doc = conn.execute(
        "SELECT * FROM registro_central WHERE pk_registro_id=?", (registro_id,)
    ).fetchone()
    if not doc:
        abort(404)
    if doc["estado"] == "Aprobado":
        flash("No se puede editar un documento ya aprobado.", "warning")
        return redirect(url_for("documentos.ver", registro_id=registro_id))

    if request.method == "POST":
        contenido = request.form.get("contenido_html","")
        asunto    = request.form.get("asunto_resumen", doc["asunto_resumen"]).strip()
        notas     = request.form.get("notas_internas", doc["notas_internas"] or "")
        plain     = re.sub(r"<[^<]+?>","",contenido)

        version = (conn.execute(
            "SELECT version FROM contenido_documento WHERE fk_registro_id=?", (registro_id,)
        ).fetchone() or {"version": 0})["version"] + 1

        conn.execute(
            "UPDATE registro_central SET asunto_resumen=?,notas_internas=? WHERE pk_registro_id=?",
            (asunto, notas, registro_id))
        conn.execute("""
            INSERT INTO contenido_documento(fk_registro_id,contenido_html,contenido_plain,version,editado_por)
            VALUES(?,?,?,?,?)
            ON CONFLICT(fk_registro_id) DO UPDATE SET
                contenido_html=excluded.contenido_html,
                contenido_plain=excluded.contenido_plain,
                version=excluded.version,
                fecha_edicion=CURRENT_TIMESTAMP,
                editado_por=excluded.editado_por
        """,(registro_id, contenido, plain, version, session.get("nombre_usuario")))
        conn.commit()
        auditar(f"Documento editado: {doc['codigo_completo']} v{version}", modulo="documentos")
        flash(f"✅ Documento actualizado (versión {version}).", "success")
        return redirect(url_for("documentos.ver", registro_id=registro_id))

    contenido = conn.execute(
        "SELECT contenido_html,version FROM contenido_documento WHERE fk_registro_id=?",
        (registro_id,)
    ).fetchone()
    contactos = conn.execute(
        "SELECT pk_contacto_id,razon_social FROM contactos WHERE activo=1 ORDER BY razon_social"
    ).fetchall()
    firmantes = conn.execute(
        "SELECT pk_firmante_id,nombre_completo,cargo FROM firmantes WHERE activo=1"
    ).fetchall()
    conn.close()

    return render_template("documentos/editar.html",
        doc=doc, contenido=contenido, areas=AREAS, tipos=TIPOS,
        contactos=contactos, firmantes=firmantes,
        plantillas=PLANTILLAS, hoy=date.today().isoformat())


# ── Cambiar estado ───────────────────────────────────────────────────
@docs_bp.route("/<int:registro_id>/cambiar_estado", methods=["POST"])
@login_requerido
def cambiar_estado(registro_id):
    nuevo_estado = request.form.get("nuevo_estado")
    observacion  = request.form.get("observacion","")
    estados_ok   = ("Borrador","En_revision","En_autorizacion","Aprobado","Rechazado","Archivado")
    if nuevo_estado not in estados_ok:
        flash("Estado no válido.", "danger")
        return redirect(url_for("documentos.ver", registro_id=registro_id))
    conn = get_db()
    doc  = conn.execute("SELECT estado FROM registro_central WHERE pk_registro_id=?",(registro_id,)).fetchone()
    if doc:
        conn.execute("UPDATE registro_central SET estado=? WHERE pk_registro_id=?",(nuevo_estado,registro_id))
        conn.execute("""
            INSERT INTO seguimiento_documento(fk_registro_id,estado_actual,estado_anterior,usuario,observaciones)
            VALUES(?,?,?,?,?)
        """,(registro_id,nuevo_estado,doc["estado"],session.get("nombre_usuario"),observacion))
        conn.commit()
        auditar(f"Estado → {nuevo_estado} doc {registro_id}", modulo="documentos")
        flash(f"Estado actualizado: {nuevo_estado}", "success")
    conn.close()
    return redirect(url_for("documentos.ver", registro_id=registro_id))


# ── Subir adjunto ────────────────────────────────────────────────────
@docs_bp.route("/<int:registro_id>/adjunto", methods=["POST"])
@login_requerido
def subir_adjunto(registro_id):
    if "archivo" not in request.files:
        flash("Sin archivo.", "warning")
        return redirect(url_for("documentos.ver", registro_id=registro_id))
    f   = request.files["archivo"]
    fn  = secure_filename(f"{registro_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{f.filename}")
    dir_= os.path.join("uploads","adjuntos")
    os.makedirs(dir_, exist_ok=True)
    ruta = os.path.join(dir_, fn)
    f.save(ruta)
    conn = get_db()
    conn.execute("""
        INSERT INTO documentos_adjuntos(fk_registro_id,nombre_archivo,ruta,tipo_archivo,tamano_bytes,subido_por)
        VALUES(?,?,?,?,?,?)
    """,(registro_id, f.filename, ruta,
         f.content_type, os.path.getsize(ruta), session.get("nombre_usuario")))
    conn.commit(); conn.close()
    flash("Adjunto subido.", "success")
    return redirect(url_for("documentos.ver", registro_id=registro_id))


# ── Generar PDF profesional ──────────────────────────────────────────
@docs_bp.route("/<int:registro_id>/pdf")
@login_requerido
def generar_pdf(registro_id):
    from core.pdf_profesional import generar_pdf_documento
    pdf_path = generar_pdf_documento(registro_id)
    if not pdf_path:
        # fallback al pdf simple
        from utils.export_pdf import generar_pdf_documento as gen_simple
        pdf_path = gen_simple(registro_id)
    if not pdf_path:
        flash("Error al generar PDF.", "danger")
        return redirect(url_for("documentos.ver", registro_id=registro_id))
    conn = get_db()
    doc  = conn.execute("SELECT codigo_completo FROM registro_central WHERE pk_registro_id=?",(registro_id,)).fetchone()
    conn.close()
    inline = request.args.get("inline","0") == "1"
    return send_file(pdf_path,
        as_attachment=not inline,
        download_name=f"{doc['codigo_completo']}.pdf",
        mimetype="application/pdf")


# ════════════════════════════════════════════════════════════
# APIs JSON para el editor (TipTap + guardado autosave)
# ════════════════════════════════════════════════════════════

@docs_bp.route("/api/borrador", methods=["POST"])
@login_requerido
def api_guardar_borrador():
    """Guardado automático (autosave cada 30s) desde el editor."""
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "Sin datos"}), 400

    conn = get_db()
    try:
        reg_id = data.get("id")
        contenido = data.get("contenido","")
        asunto    = data.get("asunto","Sin titulo").strip()
        plain     = re.sub(r"<[^<]+?>","",contenido)

        if reg_id:
            conn.execute("""
                UPDATE registro_central SET asunto_resumen=?
                WHERE pk_registro_id=?
            """,(asunto, reg_id))
            conn.execute("""
                INSERT INTO contenido_documento(fk_registro_id,contenido_html,contenido_plain,editado_por)
                VALUES(?,?,?,?)
                ON CONFLICT(fk_registro_id) DO UPDATE SET
                    contenido_html=excluded.contenido_html,
                    contenido_plain=excluded.contenido_plain,
                    fecha_edicion=CURRENT_TIMESTAMP,
                    editado_por=excluded.editado_por
            """,(reg_id, contenido, plain, session.get("nombre_usuario")))
        else:
            # Crear registro provisional
            anio  = datetime.now().year
            area  = data.get("area","GA")
            tipo  = data.get("tipo","OFI")
            consec = obtener_consecutivo(area, tipo, anio)
            codigo = f"{area}-{tipo}-{anio}-{consec:03d}"
            conn.execute("""
                INSERT INTO registro_central
                (codigo_completo,area,tipo_documento,anio,consecutivo,
                 fecha_radicacion,asunto_resumen,estado,creado_por)
                VALUES(?,?,?,?,?,?,?,'Borrador',?)
            """,(codigo,area,tipo,anio,consec,
                 data.get("fecha",date.today().isoformat()),
                 asunto, session.get("nombre_usuario")))
            reg_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
            conn.execute("""
                INSERT INTO contenido_documento(fk_registro_id,contenido_html,contenido_plain,editado_por)
                VALUES(?,?,?,?)
            """,(reg_id, contenido, plain, session.get("nombre_usuario")))

        conn.commit()
        return jsonify({"ok": True, "id": reg_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@docs_bp.route("/api/contenido/<int:registro_id>")
@login_requerido
def api_contenido(registro_id):
    """Retorna el HTML del documento para cargar en el editor."""
    conn = get_db()
    row  = conn.execute("""
        SELECT cd.contenido_html, cd.version, cd.fecha_edicion,
               r.codigo_completo, r.asunto_resumen, r.area, r.tipo_documento,
               r.fecha_radicacion, r.fk_contacto_id, r.notas_internas
        FROM contenido_documento cd
        JOIN registro_central r ON cd.fk_registro_id=r.pk_registro_id
        WHERE cd.fk_registro_id=?
    """,(registro_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"ok": False, "error": "No encontrado"}), 404
    return jsonify({"ok": True, "contenido_html": row["contenido_html"],
                    "version": row["version"], "fecha_edicion": row["fecha_edicion"],
                    "codigo": row["codigo_completo"], "asunto": row["asunto_resumen"],
                    "area": row["area"], "tipo": row["tipo_documento"]})


@docs_bp.route("/api/representante")
@login_requerido
def api_representante():
    """Datos del representante legal desde configuracion."""
    conn = get_db()
    rows = conn.execute("""
        SELECT clave, valor FROM configuracion
        WHERE clave IN ('representante_legal','cargo_representante',
                        'nombre_asociacion','nit','correo_oficial','eslogan')
    """).fetchall()
    conn.close()
    return jsonify({r["clave"]: r["valor"] for r in rows})


@docs_bp.route("/api/firmantes_activos")
@login_requerido
def api_firmantes_activos():
    """Lista de firmantes activos para insertar en el editor."""
    conn = get_db()
    rows = conn.execute("""
        SELECT pk_firmante_id as id, nombre_completo as nombre,
               cargo, whatsapp
        FROM firmantes WHERE activo=1 ORDER BY nombre_completo
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@docs_bp.route("/api/balance_hidrico_tabla")
@login_requerido
def api_balance_tabla():
    """Datos del balance hídrico para insertar como tabla en el editor."""
    anio = request.args.get("anio", datetime.now().year, type=int)
    conn = get_db()
    rows = conn.execute("""
        SELECT mes,
               COALESCE(produccion_m3,0) as p,
               COALESCE(facturado_m3,0)  as f,
               COALESCE(perdidas_m3,0)   as perd
        FROM balance_hidrico WHERE anio=? ORDER BY mes
    """,(anio,)).fetchall()
    meses = ["","Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

    # Construir tabla HTML lista para insertar en el editor
    html = f"""<table border="1" cellpadding="6" style="width:100%;border-collapse:collapse;">
<tr style="background:#1E3A8A;color:white;">
  <th>Mes</th><th>Producido m³</th><th>Facturado m³</th>
  <th>Pérdidas m³</th><th>IANC %</th>
</tr>"""
    for r in rows:
        ianc = round((r["p"]-r["f"])/r["p"]*100, 1) if r["p"] > 0 else 0
        html += f"""<tr>
  <td>{meses[r['mes']]}</td>
  <td style="text-align:right;">{r['p']:,.1f}</td>
  <td style="text-align:right;">{r['f']:,.1f}</td>
  <td style="text-align:right;">{r['perd']:,.1f}</td>
  <td style="text-align:right;{'color:red;font-weight:bold;' if ianc>25 else ''}">{ianc}%</td>
</tr>"""
    html += "</table>"
    conn.close()
    return jsonify({"ok": True, "html": html, "anio": anio})


@docs_bp.route("/api/upload/imagen", methods=["POST"])
@login_requerido
def api_upload_imagen():
    """Upload de imagen desde el editor para insertar inline."""
    if "imagen" not in request.files:
        return jsonify({"error": "Sin archivo"}), 400
    f   = request.files["imagen"]
    ext = f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else ""
    if ext not in IMG_EXTS:
        return jsonify({"error": "Tipo no permitido"}), 400
    fn  = secure_filename(f"editor_{datetime.now().strftime('%Y%m%d%H%M%S')}_{f.filename}")
    dir_= os.path.join("static","uploads","docs")
    os.makedirs(dir_, exist_ok=True)
    ruta = os.path.join(dir_, fn)
    f.save(ruta)
    return jsonify({"url": f"/static/uploads/docs/{fn}"})


@docs_bp.route("/api/upload_image", methods=["POST"])
@login_requerido
def api_upload_image_tinymce():
    """Upload de imagen compatible con TinyMCE (retorna {location:url})."""
    key = "file" if "file" in request.files else ("imagen" if "imagen" in request.files else None)
    if not key:
        return jsonify({"error": "Sin archivo"}), 400
    f   = request.files[key]
    ext = f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else ""
    if ext not in {"jpg","jpeg","png","gif","webp","svg"}:
        return jsonify({"error": "Tipo no permitido"}), 400
    fn  = secure_filename(f"editor_{datetime.now().strftime('%Y%m%d%H%M%S')}_{f.filename}")
    dir_= os.path.join("static","uploads","docs")
    os.makedirs(dir_, exist_ok=True)
    f.save(os.path.join(dir_, fn))
    return jsonify({"location": f"/static/uploads/docs/{fn}"})


@docs_bp.route("/api/plantilla/<nombre>")
@login_requerido
def api_plantilla(nombre):
    """Retorna el HTML de una plantilla predefinida."""
    p = PLANTILLAS.get(nombre)
    if not p:
        return jsonify({"ok": False, "error": "Plantilla no encontrada"}), 404
    return jsonify({"ok": True, "html": p["html"], "nombre": p["nombre"]})


@docs_bp.route("/api/stats")
@login_requerido
def api_stats():
    """Estadísticas del módulo de documentos."""
    conn = get_db()
    hoy  = date.today().isoformat()
    stats = {
        "total":         conn.execute("SELECT COUNT(*) as c FROM registro_central").fetchone()["c"],
        "borradores":    conn.execute("SELECT COUNT(*) as c FROM registro_central WHERE estado='Borrador'").fetchone()["c"],
        "en_revision":   conn.execute("SELECT COUNT(*) as c FROM registro_central WHERE estado='En_revision'").fetchone()["c"],
        "en_autorizacion": conn.execute("SELECT COUNT(*) as c FROM registro_central WHERE estado='En_autorizacion'").fetchone()["c"],
        "aprobados":     conn.execute("SELECT COUNT(*) as c FROM registro_central WHERE estado='Aprobado'").fetchone()["c"],
        "vencidos":      conn.execute("SELECT COUNT(*) as c FROM registro_central WHERE fecha_vencimiento<? AND estado NOT IN('Aprobado','Archivado','Rechazado')",(hoy,)).fetchone()["c"],
        "este_mes":      conn.execute("SELECT COUNT(*) as c FROM registro_central WHERE strftime('%Y-%m',fecha_radicacion)=strftime('%Y-%m','now')").fetchone()["c"],
    }
    por_area = conn.execute("""
        SELECT area, COUNT(*) as c FROM registro_central GROUP BY area ORDER BY c DESC
    """).fetchall()
    stats["por_area"] = [dict(r) for r in por_area]
    conn.close()
    return jsonify(stats)


@docs_bp.route("/api/buscar")
@login_requerido
def api_buscar_codigo():
    """Busca documentos por código exacto o parcial. Usado desde proyectos (PROGRAMA_5)."""
    codigo = request.args.get("codigo","").strip()
    q      = request.args.get("q","").strip()
    conn   = get_db()
    if codigo:
        row = conn.execute("""
            SELECT pk_registro_id as id, codigo_completo as codigo,
                   asunto_resumen as asunto, fecha_radicacion as fecha, estado
            FROM registro_central WHERE codigo_completo=?
        """, (codigo,)).fetchone()
        conn.close()
        return jsonify(dict(row) if row else {"error": "No encontrado"}), (200 if row else 404)
    elif q:
        rows = conn.execute("""
            SELECT pk_registro_id as id, codigo_completo as codigo,
                   asunto_resumen as asunto, fecha_radicacion as fecha, estado
            FROM registro_central
            WHERE codigo_completo LIKE ? OR asunto_resumen LIKE ?
            ORDER BY fecha_radicacion DESC LIMIT 15
        """, (f"%{q}%", f"%{q}%")).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    conn.close()
    return jsonify({"error": "Parámetro q o codigo requerido"}), 400


@docs_bp.route("/api/proyecto/<int:pid>", methods=["POST"])
@login_requerido
def api_asociar_a_proyecto(pid):
    """Asocia el documento recién guardado a un proyecto (PROGRAMA_5)."""
    data   = request.get_json() or {}
    doc_id = data.get("documento_id")
    tipo   = data.get("tipo_relacion", "soporte")
    if not doc_id:
        return jsonify({"ok": False}), 400
    conn = get_db()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO documentos_proyecto
            (documento_id, proyecto_id, tipo_relacion)
            VALUES (?,?,?)
        """, (doc_id, pid, tipo))
        conn.commit(); conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        conn.rollback(); conn.close()
        return jsonify({"ok": False, "error": str(e)}), 500

@docs_bp.route("/api/tipos")
@login_requerido
def api_tipos_documento():
    """Lista tipos de documento: primero BD, fallback a TIPOS hardcodeado."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT codigo, nombre, activo FROM tipos_documento WHERE activo=1 ORDER BY nombre"
        ).fetchall()
        if rows:
            return jsonify([dict(r) for r in rows])
    except Exception:
        pass
    finally:
        conn.close()
    return jsonify([{"codigo": c, "nombre": n} for c, n in TIPOS])

@docs_bp.route("/api/ia_proxy", methods=["POST"])
@login_requerido
def api_ia_proxy():
    """Proxy seguro hacia Claude API — evita CORS y oculta la clave."""
    import requests as _req
    from core.database_manager import get_db as _gdb
    data = request.get_json(silent=True) or {}
    instruccion = data.get("instruccion","").strip()
    contexto    = data.get("contexto","").strip()
    if not instruccion:
        return jsonify({"ok":False,"error":"Instrucción vacía"}), 400

    # Obtener API key desde BD o variable de entorno
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY","")
    if not api_key:
        try:
            conn = _gdb()
            r = conn.execute("SELECT valor FROM configuracion WHERE clave='anthropic_api_key'").fetchone()
            conn.close()
            api_key = r["valor"] if r and r["valor"] else ""
        except: pass

    if not api_key:
        return jsonify({"ok":False,
            "error":"Sin clave API. Configure ANTHROPIC_API_KEY en Configuración > Notificaciones."}), 503

    prompt = f"""{contexto}

INSTRUCCIÓN: {instruccion}

REGLAS: Tono formal colombiano. Sin markdown, solo texto plano con saltos de línea.
Si es tabla: usa | para separar columnas. Máximo 400 palabras."""

    try:
        resp = _req.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1000,
                "messages": [{"role":"user","content":prompt}]
            },
            timeout=30
        )
        d = resp.json()
        if resp.status_code == 200:
            texto = "".join(b.get("text","") for b in d.get("content",[]) if b.get("type")=="text")
            return jsonify({"ok":True,"texto":texto})
        else:
            return jsonify({"ok":False,"error":d.get("error",{}).get("message","Error API")}), resp.status_code
    except Exception as e:
        return jsonify({"ok":False,"error":f"Sin conexión a internet: {e}"}), 503

