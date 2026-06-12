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
import re, os, json, tempfile, logging as _logging
_log_docs = _logging.getLogger("sigca.documentos")

# gestor_trd — importación condicional (#41)
try:
    from core.gestor_trd import gestor_trd
    _GESTOR_TRD_AVAILABLE = True
except ImportError:
    gestor_trd = None
    _GESTOR_TRD_AVAILABLE = False
from io import BytesIO
import hashlib
import secrets
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, send_file, abort, jsonify)
from werkzeug.utils import secure_filename
from core.database_manager import get_db, atomic, readonly, validar_columnas, obtener_consecutivo, registrar_log, db_connection
from core.seguridad import login_requerido
from utils.seguridad import verificar_token_csrf
from core.rate_limiter import limitar
from core.capability_registry import CapabilityRegistry
from core.auditoria import auditar, registrar_evento
from core.forensic_saneamiento import SaneadorForense
from datetime import datetime, timedelta, date

# Clasificador archivístico — disponibilidad verificada al cargar el módulo (#6)
try:
    from core.document_classifier import (
        clasificar_documento as _clf_doc,
        enriquecer_registro as _enriquecer_registro,
    )
    CLASSIFIER_AVAILABLE = True
except ImportError:
    CLASSIFIER_AVAILABLE = False
    _log_docs.warning("core/document_classifier.py no encontrado. Clasificación TRD desactivada.")



# ============================================================
# HELPERS v4
# ============================================================

def generar_hash_contenido(registro_id: int, contenido: str, usuario: str) -> str:
    datos = f"{registro_id}|{contenido}|{datetime.now().isoformat()}|{usuario}"
    return hashlib.sha256(datos.encode('utf-8')).hexdigest()


def verificar_ownership(conn, documento_id: int, usuario: str) -> bool:
    doc = conn.execute(
        "SELECT creado_por FROM registro_central WHERE pk_registro_id = ?",
        (documento_id,)
    ).fetchone()
    if not doc:
        return False
    return (doc['creado_por'] == usuario or
            session.get('rol') in ('admin', 'supervisor'))


def registrar_acceso_doc(conn, doc_id: int, usuario: str, ip: str) -> None:
    try:
        conn.execute("""
            INSERT INTO acceso_documentos
            (documento_id, usuario, usuario_nombre, ip_origen, fecha_acceso, accion)
            VALUES (?, ?, ?, ?, ?, 'VER')
        """, (doc_id, usuario, usuario, ip, datetime.now().isoformat()))
    except Exception:
        pass


def calcular_vencimiento_trd(conn, doc_id: int):
    """Retorna días restantes en Gestión según TRD. Usa document_classifier como fuente única."""
    if not CLASSIFIER_AVAILABLE:
        return None
    try:
        row = conn.execute(
            "SELECT tipo_documento, asunto_resumen, area, fecha_radicacion FROM registro_central WHERE pk_registro_id=?",
            (doc_id,)
        ).fetchone()
        if not row or not row["fecha_radicacion"]:
            return None
        clf = _clf_doc(row["tipo_documento"] or "", row["asunto_resumen"] or "", row["area"])
        fecha_rad = datetime.strptime(row["fecha_radicacion"], "%Y-%m-%d").date()
        try:
            vence = fecha_rad.replace(year=fecha_rad.year + clf.retencion_gestion)
        except ValueError:
            vence = fecha_rad + timedelta(days=clf.retencion_gestion * 365)
        return (vence - date.today()).days
    except Exception:
        return None

docs_bp = Blueprint("documentos", __name__, url_prefix="/documentos")

AREAS = [("GA","Gestion Ambiental"),("GC","Gestion Comercial"),
         ("GF","Gestion Financiera"),("GE","Gestion Estrategica"),
         ("GL","Gestion Legal")]
TIPOS = [
    ("OFI","Oficio"),("ACT","Acta"),("RES","Resolucion"),
    ("INF","Informe"),("OT","Orden de Trabajo"),("OC","Orden de Compra"),
    ("PQR","PQRS"),("CON","Convenio / Contrato"),("COT","Cotizacion"),
    ("CIR","Circular"),("REQ","Contestacion Requerimiento Fiscal"),
    ("ASEXR","Asistencia Extrapresupuestaria Rodamiento"),
    ("CCB","Cuenta de Cobro"),("CDP","Disponibilidad Presupuestal"),
    ("CER","Certificado"),("CL","Certificado de Libertad"),
    ("CONV","Convocatoria"),("CRP","Certificado de Registro Presupuestal"),
    ("CUU","Contrato Condiciones Uniformes"),("ESF","Estados Financieros"),
    ("EVA","Evaluacion de Desempeno"),("FM","Formato / Plantilla"),
    ("FOR","Formulario"),("HV","Hoja de Vida"),
    ("IND","Indicador de Gestion"),("INV","Inventario"),
    ("LIC","Licencia / Permiso"),("LMCRO","Lectura Macromedidor"),
    ("MAN","Manual"),("MEM","Memorando"),
    ("MIC","Lectura Micromedidor"),("PLA","Plan"),
    ("POL","Politica"),("PRE","Presupuesto"),
    ("RAL","Respuesta a Alcaldia"),("RCAR","Respuesta a CAR"),
    ("RIE","Matriz de Riesgos"),("RP","Registro Presupuestal"),
    ("RSSPD","Respuesta / Reporte a SSPD"),("SOL","Solicitud Individual"),
    ("EST","Estudio"),("ACP","Acuerdo de Pago"),
    ("P","Procedimiento"),
]

IMG_EXTS = {"png","jpg","jpeg","gif","webp","svg"}

PLANTILLAS = {
    "oficio_car": {
        "nombre": "Oficio a la CAR",
        "html": """<p><strong>Senores</strong><br>
CORPORACION AUTONOMA REGIONAL DE CUNDINAMARCA - CAR<br>
Oficina Regional Gualiiva<br>
Ciudad</p>
<p>Asunto: [ASUNTO]</p>
<p>Respetados senores:</p>
<p>Por medio del presente, la Asociacion de Suscriptores del Acueducto Comunitario
El Puente - PARAGUASMJ, identificada con NIT 832.001.389-2, con domicilio en el
Caserio El Puente, Villeta, Cundinamarca, se permite [ACCION].</p>
<p>Para mayor informacion, quedamos atentos en nuestras oficinas ubicadas en
el Caserio El Puente, Villeta, Cundinamarca.</p>
<p>Cordialmente,</p>"""
    },
    "acta_reunion": {
        "nombre": "Acta de Reunion",
        "html": """<h2>ACTA DE REUNION</h2>
<table border="1" cellpadding="8" style="width:100%;border-collapse:collapse;">
  <tr><td><strong>Fecha:</strong></td><td>[FECHA]</td><td><strong>Hora inicio:</strong></td><td></td></tr>
  <tr><td><strong>Lugar:</strong></td><td colspan="3">Sede - Caserio El Puente, Villeta</td></tr>
  <tr><td><strong>Convocatoria:</strong></td><td colspan="3">Junta Directiva PARAGUASMJ</td></tr>
</table>
<h3>1. Asistentes</h3>
<table border="1" cellpadding="6" style="width:100%;border-collapse:collapse;">
  <tr><th>Nombre</th><th>Cargo</th><th>Firma</th></tr>
  <tr><td></td><td></td><td></td></tr>
</table>
<h3>2. Orden del Dia</h3>
<ol><li></li><li></li><li></li></ol>
<h3>3. Desarrollo de la Reunion</h3>
<p></p>
<h3>4. Compromisos y Responsables</h3>
<table border="1" cellpadding="6" style="width:100%;border-collapse:collapse;">
  <tr><th>Compromiso</th><th>Responsable</th><th>Fecha limite</th></tr>
  <tr><td></td><td></td><td></td></tr>
</table>
<h3>5. Cierre</h3>
<p>No habiendo mas asuntos que tratar, se levanta la sesion a las ___ horas.</p>"""
    },
    "contestacion_fiscal": {
        "nombre": "Contestacion Requerimiento Fiscal",
        "html": """<h2>CONTESTACION A REQUERIMIENTO FISCAL</h2>
<table border="1" cellpadding="8" style="width:100%;border-collapse:collapse;">
  <tr><td><strong>Radicado requerimiento:</strong></td><td></td></tr>
  <tr><td><strong>Entidad requirente:</strong></td><td></td></tr>
  <tr><td><strong>Fecha notificacion:</strong></td><td></td></tr>
  <tr><td><strong>Valor cuestionado:</strong></td><td></td></tr>
</table>
<h3>I. POSICION JURIDICA</h3>
<p>La Asociacion PARAGUASMJ, actuando de buena fe y en ejercicio del derecho de defensa
consagrado en el articulo 29 de la Constitucion Politica de Colombia, se permite
manifestar su posicion frente a los hechos imputados:</p>
<h3>II. DESCRIPCION DE LOS HECHOS</h3>
<h4>EJE 1:</h4>
<table border="1" cellpadding="6" style="width:100%;border-collapse:collapse;">
  <tr><th>Tiempo</th><th>Modo</th><th>Lugar</th><th>Valor</th><th>Responsable</th></tr>
  <tr><td></td><td></td><td></td><td></td><td></td></tr>
</table>
<h3>III. SOLICITUDES</h3>
<ol><li>Declarar exonerada a PARAGUASMJ de la responsabilidad fiscal imputada.</li>
    <li>[OTRAS SOLICITUDES]</li></ol>"""
    },
    "acta_entrega_materiales": {
        "nombre": "Acta Entrega de Materiales",
        "html": """<h2>ACTA DE ENTREGA DE MATERIALES</h2>
<table border="1" cellpadding="8" style="width:100%;border-collapse:collapse;">
  <tr><td><strong>Orden de Compra:</strong></td><td></td><td><strong>Fecha:</strong></td><td></td></tr>
  <tr><td><strong>Proveedor:</strong></td><td colspan="3"></td></tr>
</table>
<h3>Relacion de Materiales Entregados</h3>
<table border="1" cellpadding="6" style="width:100%;border-collapse:collapse;">
  <tr><th>N</th><th>Descripcion</th><th>Unidad</th><th>Cantidad</th><th>Precio Unit.</th><th>Total</th></tr>
  <tr><td>1</td><td></td><td></td><td></td><td></td><td></td></tr>
  <tr><td colspan="5"><strong>TOTAL</strong></td><td></td></tr>
</table>
<p>La persona que suscribe declara recibir a satisfaccion los materiales relacionados.</p>"""
    },
    "oficio_sspd": {
        "nombre": "Oficio a la SSPD",
        "html": """<p><strong>Senores</strong><br>
SUPERINTENDENCIA DE SERVICIOS PUBLICOS DOMICILIARIOS - SSPD<br>
Bogota D.C.</p>
<p>Asunto: Remision de informacion SUI - Ano [ANNO]</p>
<p>Respetados senores:</p>
<p>PARAGUASMJ, prestador de los servicios de acueducto y alcantarillado con codigo SUI
[CODIGO_SUI], da cumplimiento a la obligacion de reporte periodico de informacion
al Sistema Unico de Informacion, en los terminos del articulo 14 de la Ley 142 de
1994 y la Resolucion SSPD [RESOLUCION].</p>
<p>Se adjuntan los formularios FC01, FC03 y FC15 debidamente diligenciados.</p>"""
    }
}


# ── Funciones auxiliares ──────────────────────────────────────────────────────

def sanitizar_html(html_content: str) -> str:
    if not html_content:
        return ""
    MAX = 2 * 1024 * 1024
    if len(html_content) > MAX:
        html_content = html_content[:MAX]
    html_content = re.sub(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", "", html_content, flags=re.I | re.S)
    html_content = re.sub(r"\son\w+\s*=", " data-removed=", html_content)
    return html_content


def validar_fecha(fecha_str: str) -> bool:
    try:
        f = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        return 1900 <= f.year <= 2100
    except (ValueError, TypeError):
        return False


def crear_directorio_upload(path: str) -> bool:
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception:
        return False


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

    conn = None
    try:
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

        return render_template("documentos/lista.html", documentos=docs,
            areas=AREAS, tipos=TIPOS,
            area_sel=area, estado_sel=estado, tipo_sel=tipo, q=q,
            pagina=pagina, total_pags=(total+por_pag-1)//por_pag,
            total=total, stats=stats)
    finally:
        if conn: conn.close()


# ── Nuevo documento ─────────────────────────────────────────────────
@docs_bp.route("/nuevo", methods=["GET","POST"])
@login_requerido
def nuevo():
    conn = None
    try:
        conn = get_db()

        if request.method == "POST":
            if not verificar_token_csrf():
                flash("Token de seguridad invalido. Recargue la pagina.", "danger")
                return redirect(url_for("documentos.nuevo"))
            area        = request.form["area"]
            tipo        = request.form["tipo_documento"]
            anio        = datetime.now().year
            asunto      = request.form["asunto_resumen"].strip()
            fecha_rad   = request.form.get("fecha_radicacion") or date.today().isoformat()
            fk_contacto = request.form.get("fk_contacto_id") or None
            notas       = request.form.get("notas_internas","")
            contenido   = sanitizar_html(request.form.get("contenido_html",""))
            fecha_venc  = request.form.get("fecha_vencimiento") or None
            firmantes_sel = request.form.getlist("firmantes_sel")

            try:
                consec  = obtener_consecutivo(area, tipo, anio)
                codigo  = f"{area}-{tipo}-{anio}-{consec:03d}"
                fecha_r = datetime.strptime(fecha_rad, "%Y-%m-%d")
                cfg_row = conn.execute("SELECT clave,valor FROM configuracion WHERE clave IN ('dias_alerta_documentos','dias_plazo_autorizacion')").fetchall()
                cfg     = {r["clave"]: int(r["valor"]) for r in cfg_row}
                dias_al = cfg.get("dias_alerta_documentos", 4)
                dias_pl = cfg.get("dias_plazo_autorizacion", 7)

                trd_row = conn.execute(
                    "SELECT pk_trd_id FROM trd WHERE area=? AND (tipo_documento=? OR tipo_documento IS NULL) ORDER BY tipo_documento IS NOT NULL DESC LIMIT 1",
                    (area, tipo)
                ).fetchone()
                fk_trd = trd_row["pk_trd_id"] if trd_row else None

                _baseline_meta = json.dumps(
                    CapabilityRegistry().get_document_metadata(),
                    ensure_ascii=False, separators=(",", ":")
                )
                conn.execute("""
                    INSERT INTO registro_central
                    (codigo_completo,area,tipo_documento,anio,consecutivo,fecha_radicacion,
                     fecha_vencimiento,fk_contacto_id,asunto_resumen,notas_internas,estado,creado_por,
                     indicador_activo,fase_archivo,fecha_ingreso_fase,fk_trd_id,activo,baseline_metadata)
                    VALUES(?,?,?,?,?,?,?,?,?,?,'Borrador',?,1,'Gestion',?,?,1,?)
                """,(codigo,area,tipo,anio,consec,fecha_rad,fecha_venc,fk_contacto,asunto,notas,
                     session.get("nombre_usuario"), date.today().isoformat(), fk_trd, _baseline_meta))
                reg_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]

                plain = re.sub(r"<[^<]+?>","",contenido)
                conn.execute("""
                    INSERT INTO contenido_documento
                    (fk_registro_id,contenido_html,contenido_plain,editado_por)
                    VALUES(?,?,?,?)
                """,(reg_id, contenido, plain, session.get("nombre_usuario")))

                conn.execute("""
                    INSERT INTO plazos_documento(fk_registro_id,fecha_inicio_notificaciones)
                    VALUES(?,?)
                """,(reg_id, (fecha_r+timedelta(days=dias_al)).date().isoformat()))

                fl_accion = (fecha_r+timedelta(days=dias_pl)).date().isoformat()

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

                # Clasificación archivística determinística — obligatoria (#2, #6)
                if CLASSIFIER_AVAILABLE:
                    clf = _clf_doc(tipo, asunto, area)
                    if fk_trd is None and clf.serie_codigo != "OTR":
                        trd_auto = conn.execute(
                            "SELECT pk_trd_id FROM trd WHERE nombre LIKE ? LIMIT 1",
                            (f"%{clf.serie_nombre}%",)
                        ).fetchone()
                        if trd_auto:
                            conn.execute(
                                "UPDATE registro_central SET fk_trd_id=? WHERE pk_registro_id=?",
                                (trd_auto["pk_trd_id"], reg_id)
                            )
                else:
                    flash("Advertencia: clasificador TRD no disponible. Asigne la serie manualmente.", "warning")

                conn.commit()
                auditar(f"Documento creado: {codigo}", modulo="documentos")
                flash(f"Documento {codigo} creado exitosamente.", "success")
                return redirect(url_for("documentos.ver", registro_id=reg_id))

            except Exception as e:
                conn.rollback()
                _log_docs.error("crear documento: %s", e, exc_info=True)
                flash("Error al crear el documento. Contacte al administrador.", "danger")

        contactos  = conn.execute(
            "SELECT pk_contacto_id,razon_social FROM contactos WHERE activo=1 ORDER BY razon_social"
        ).fetchall()
        firmantes  = conn.execute(
            "SELECT pk_firmante_id,nombre_completo,cargo FROM firmantes WHERE activo=1 ORDER BY nombre_completo"
        ).fetchall()

        try:
            conn2 = get_db()
            ia_row = conn2.execute("SELECT valor FROM configuracion WHERE clave='anthropic_api_key'").fetchone()
            tiene_ia = bool(ia_row and ia_row["valor"] and ia_row["valor"].strip())
            conn2.close()
        except Exception:
            tiene_ia = False

        return render_template("documentos/nuevo.html",
            areas=AREAS, tipos=TIPOS, contactos=contactos,
            firmantes=firmantes, plantillas=PLANTILLAS,
            hoy=date.today().isoformat(), tiene_ia=tiene_ia)
    finally:
        if conn: conn.close()


# ── Ver documento ────────────────────────────────────────────────────
@docs_bp.route("/<int:registro_id>")
@login_requerido
def ver(registro_id):
    conn = None
    try:
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

        return render_template("documentos/ver.html", doc=doc,
            contenido=contenido, adjuntos=adjuntos, seguimiento=seguim,
            acciones=acciones, otps=otps, firmantes_doc=firmantes_doc,
            areas=AREAS, tipos=TIPOS)
    finally:
        if conn: conn.close()


def _obtener_timestamp_seguro(fecha_edicion) -> int:
    """
    Convierte fecha_edicion a timestamp Unix en segundos.
    Maneja string SQLite ("2026-06-07 08:36:55"), ISO 8601 con T,
    microsegundos, y objetos datetime. Devuelve 0 ante cualquier fallo.
    """
    if not fecha_edicion:
        return 0
    try:
        if isinstance(fecha_edicion, datetime):
            return int(fecha_edicion.timestamp())
        s = str(fecha_edicion).replace("T", " ").split(".")[0].strip()
        return int(datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timestamp())
    except (ValueError, TypeError, AttributeError):
        return 0


# ── Editar contenido ──────────────────────────────────────────────────
@docs_bp.route("/<int:registro_id>/editar", methods=["GET","POST"])
@login_requerido
def editar(registro_id):
    conn = None
    try:
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
            if not verificar_token_csrf():
                flash("Token de seguridad invalido. Recargue la pagina.", "danger")
                return redirect(url_for("documentos.editar", registro_id=registro_id))
            contenido = sanitizar_html(request.form.get("contenido_html",""))
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
            flash(f"Documento actualizado (version {version}).", "success")
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

        fe = (dict(contenido).get("fecha_edicion") if contenido else None) \
             or dict(doc).get("fecha_modificacion")
        # Segundos Unix → JS multiplica por 1000 para comparar con Date.now()
        fecha_servidor_segundos = _obtener_timestamp_seguro(fe)

        return render_template("documentos/editar.html",
            doc=doc, contenido=contenido, areas=AREAS, tipos=TIPOS,
            contactos=contactos, firmantes=firmantes,
            plantillas=PLANTILLAS, hoy=date.today().isoformat(),
            fecha_servidor_segundos=fecha_servidor_segundos)
    finally:
        if conn: conn.close()


# ── Cambiar estado ───────────────────────────────────────────────────
@docs_bp.route("/<int:registro_id>/cambiar_estado", methods=["POST"])
@login_requerido
def cambiar_estado(registro_id):
    if not verificar_token_csrf():
        flash("Token de seguridad invalido.", "danger")
        return redirect(url_for("documentos.ver", registro_id=registro_id))
    nuevo_estado = request.form.get("nuevo_estado")
    observacion  = request.form.get("observacion","")
    estados_ok   = ("Borrador","En_revision","En_autorizacion","Aprobado","Rechazado","Archivado")
    if nuevo_estado not in estados_ok:
        flash("Estado no valido.", "danger")
        return redirect(url_for("documentos.ver", registro_id=registro_id))
    conn = None
    try:
        conn = get_db()
        doc  = conn.execute("SELECT estado FROM registro_central WHERE pk_registro_id=?",(registro_id,)).fetchone()
        if doc:
            conn.execute("UPDATE registro_central SET estado=? WHERE pk_registro_id=?",(nuevo_estado,registro_id))
            conn.execute("""
                INSERT INTO seguimiento_documento(fk_registro_id,estado_actual,estado_anterior,usuario,observaciones)
                VALUES(?,?,?,?,?)
            """,(registro_id,nuevo_estado,doc["estado"],session.get("nombre_usuario"),observacion))
            conn.commit()
            auditar(f"Estado -> {nuevo_estado} doc {registro_id}", modulo="documentos")
            flash(f"Estado actualizado: {nuevo_estado}", "success")
        return redirect(url_for("documentos.ver", registro_id=registro_id))
    finally:
        if conn: conn.close()


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
    conn = None
    try:
        conn = get_db()
        conn.execute("""
            INSERT INTO documentos_adjuntos(fk_registro_id,nombre_archivo,ruta,tipo_archivo,tamano_bytes,subido_por)
            VALUES(?,?,?,?,?,?)
        """,(registro_id, f.filename, ruta,
             f.content_type, os.path.getsize(ruta), session.get("nombre_usuario")))
        conn.commit()
        flash("Adjunto subido.", "success")
        return redirect(url_for("documentos.ver", registro_id=registro_id))
    finally:
        if conn: conn.close()


# ── Generar PDF ──────────────────────────────────────────────────────
@docs_bp.route("/<int:registro_id>/pdf")
@login_requerido
def generar_pdf(registro_id):
    from core.pdf_profesional import generar_pdf_documento
    pdf_path = generar_pdf_documento(registro_id)
    if not pdf_path:
        from utils.export_pdf import generar_pdf_documento as gen_simple
        pdf_path = gen_simple(registro_id)
    if not pdf_path:
        flash("Error al generar PDF.", "danger")
        return redirect(url_for("documentos.ver", registro_id=registro_id))
    conn = None
    try:
        conn = get_db()
        doc  = conn.execute("SELECT codigo_completo FROM registro_central WHERE pk_registro_id=?",(registro_id,)).fetchone()
        inline = request.args.get("inline","0") == "1"
        return send_file(pdf_path,
            as_attachment=not inline,
            download_name=f"{doc['codigo_completo']}.pdf",
            mimetype="application/pdf")
    finally:
        if conn: conn.close()


# ════════════════════════════════════════════════════════════
# APIs JSON para el editor
# ════════════════════════════════════════════════════════════

@docs_bp.route("/api/borrador", methods=["POST"])
@login_requerido
def api_guardar_borrador():
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "Sin datos"}), 400

    conn = get_db()
    try:
        reg_id    = data.get("id") or session.get("borrador_actual_id")
        contenido = data.get("contenido","")
        asunto    = data.get("asunto","Sin titulo").strip()
        plain     = re.sub(r"<[^<]+?>","",contenido)

        if reg_id:
            conn.execute("UPDATE registro_central SET asunto_resumen=? WHERE pk_registro_id=?",(asunto, reg_id))
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
            anio   = datetime.now().year
            area   = data.get("area","GA")
            tipo   = data.get("tipo","OFI")
            consec = obtener_consecutivo(area, tipo, anio)
            codigo = f"{area}-{tipo}-{anio}-{consec:03d}"
            _bm = json.dumps(
                CapabilityRegistry().get_document_metadata(),
                ensure_ascii=False, separators=(",", ":")
            )
            conn.execute("""
                INSERT INTO registro_central
                (codigo_completo,area,tipo_documento,anio,consecutivo,
                 fecha_radicacion,asunto_resumen,estado,creado_por,baseline_metadata)
                VALUES(?,?,?,?,?,?,?,'Borrador',?,?)
            """,(codigo,area,tipo,anio,consec,
                 data.get("fecha",date.today().isoformat()),
                 asunto, session.get("nombre_usuario"), _bm))
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
    conn = None
    try:
        conn = get_db()
        row  = conn.execute("""
            SELECT cd.contenido_html, cd.version, cd.fecha_edicion,
                   r.codigo_completo, r.asunto_resumen, r.area, r.tipo_documento,
                   r.fecha_radicacion, r.fk_contacto_id, r.notas_internas
            FROM contenido_documento cd
            JOIN registro_central r ON cd.fk_registro_id=r.pk_registro_id
            WHERE cd.fk_registro_id=?
        """,(registro_id,)).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "No encontrado"}), 404
        return jsonify({"ok": True, "contenido_html": row["contenido_html"],
                        "version": row["version"], "fecha_edicion": row["fecha_edicion"],
                        "codigo": row["codigo_completo"], "asunto": row["asunto_resumen"],
                        "area": row["area"], "tipo": row["tipo_documento"]})
    finally:
        if conn: conn.close()


@docs_bp.route("/api/representante")
@login_requerido
def api_representante():
    conn = None
    try:
        conn = get_db()
        rows = conn.execute("""
            SELECT clave, valor FROM configuracion
            WHERE clave IN ('representante_legal','cargo_representante',
                            'nombre_asociacion','nit','correo','eslogan')
        """).fetchall()
        return jsonify({r["clave"]: r["valor"] for r in rows})
    finally:
        if conn: conn.close()


@docs_bp.route("/api/firmantes_activos")
@login_requerido
def api_firmantes_activos():
    conn = None
    try:
        conn = get_db()
        rows = conn.execute("""
            SELECT pk_firmante_id as id, nombre_completo as nombre,
                   cargo, whatsapp
            FROM firmantes WHERE activo=1 ORDER BY nombre_completo
        """).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        if conn: conn.close()


@docs_bp.route("/api/balance_hidrico_tabla")
@login_requerido
def api_balance_tabla():
    anio = request.args.get("anio", datetime.now().year, type=int)
    conn = None
    try:
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
        html = f"""<table border="1" cellpadding="6" style="width:100%;border-collapse:collapse;">
    <tr style="background:#1E3A8A;color:white;">
      <th>Mes</th><th>Producido m3</th><th>Facturado m3</th>
      <th>Perdidas m3</th><th>IANC %</th>
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
        return jsonify({"ok": True, "html": html, "anio": anio})
    finally:
        if conn: conn.close()


@docs_bp.route("/api/upload/imagen", methods=["POST"])
@login_requerido
def api_upload_imagen():
    if "imagen" not in request.files:
        return jsonify({"error": "Sin archivo"}), 400
    f   = request.files["imagen"]
    ext = f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else ""
    if ext not in IMG_EXTS:
        return jsonify({"error": "Tipo no permitido"}), 400
    dir_ = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "static", "uploads", "docs"
    ))
    try:
        from utils.compresor_imagen import guardar_imagen_comprimida
        _, fn = guardar_imagen_comprimida(f, dir_, prefix="img")
    except Exception:
        fn   = secure_filename(f"editor_{datetime.now().strftime('%Y%m%d%H%M%S')}_{f.filename}")
        ruta = os.path.join(dir_, fn)
        f.save(ruta)
    return jsonify({"url": f"/static/uploads/docs/{fn}"})


@docs_bp.route("/api/plantilla/<nombre>")
@login_requerido
def api_plantilla(nombre):
    p = PLANTILLAS.get(nombre)
    if not p:
        return jsonify({"ok": False, "error": "Plantilla no encontrada"}), 404
    return jsonify({"ok": True, "html": p["html"], "nombre": p["nombre"]})


@docs_bp.route("/api/stats")
@login_requerido
def api_stats():
    conn = None
    try:
        conn = get_db()
        hoy  = date.today().isoformat()
        stats = {
            "total":           conn.execute("SELECT COUNT(*) as c FROM registro_central").fetchone()["c"],
            "borradores":      conn.execute("SELECT COUNT(*) as c FROM registro_central WHERE estado='Borrador'").fetchone()["c"],
            "en_revision":     conn.execute("SELECT COUNT(*) as c FROM registro_central WHERE estado='En_revision'").fetchone()["c"],
            "en_autorizacion": conn.execute("SELECT COUNT(*) as c FROM registro_central WHERE estado='En_autorizacion'").fetchone()["c"],
            "aprobados":       conn.execute("SELECT COUNT(*) as c FROM registro_central WHERE estado='Aprobado'").fetchone()["c"],
            "vencidos":        conn.execute("SELECT COUNT(*) as c FROM registro_central WHERE fecha_vencimiento<? AND estado NOT IN('Aprobado','Archivado','Rechazado')",(hoy,)).fetchone()["c"],
            "este_mes":        conn.execute("SELECT COUNT(*) as c FROM registro_central WHERE strftime('%Y-%m',fecha_radicacion)=strftime('%Y-%m','now')").fetchone()["c"],
        }
        por_area = conn.execute("""
            SELECT area, COUNT(*) as c FROM registro_central GROUP BY area ORDER BY c DESC
        """).fetchall()
        stats["por_area"] = [dict(r) for r in por_area]
        return jsonify(stats)
    finally:
        if conn: conn.close()


@docs_bp.route("/api/buscar")
@login_requerido
def api_buscar_codigo():
    codigo = request.args.get("codigo","").strip()
    q      = request.args.get("q","").strip()
    conn   = get_db()
    try:
        if codigo:
            row = conn.execute("""
                SELECT pk_registro_id as id, codigo_completo as codigo,
                       asunto_resumen as asunto, fecha_radicacion as fecha, estado
                FROM registro_central WHERE codigo_completo=?
            """, (codigo,)).fetchone()
            return jsonify(dict(row) if row else {"error": "No encontrado"}), (200 if row else 404)
        elif q:
            rows = conn.execute("""
                SELECT pk_registro_id as id, codigo_completo as codigo,
                       asunto_resumen as asunto, fecha_radicacion as fecha, estado
                FROM registro_central
                WHERE codigo_completo LIKE ? OR asunto_resumen LIKE ?
                ORDER BY fecha_radicacion DESC LIMIT 15
            """, (f"%{q}%", f"%{q}%")).fetchall()
            return jsonify([dict(r) for r in rows])
        return jsonify({"error": "Parametro q o codigo requerido"}), 400
    finally:
        conn.close()


@docs_bp.route("/api/proyecto/<int:pid>", methods=["POST"])
@login_requerido
def api_asociar_a_proyecto(pid):
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
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@docs_bp.route("/api/tipos")
@login_requerido
def api_tipos_documento():
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


# ── Exportar DOCX ────────────────────────────────────────────────
@docs_bp.route("/<int:registro_id>/docx")
@login_requerido
def generar_docx(registro_id):
    """Exporta documento institucional a Word (.docx) — sin escritura a disco."""
    try:
        from docx import Document as DocxDocument
        from docx.shared import Pt
        from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
    except ImportError:
        flash("Modulo python-docx no instalado. Ejecute: pip install python-docx>=1.1.0", "danger")
        return redirect(url_for("documentos.ver", registro_id=registro_id))

    with db_connection(autocommit=False) as conn:
        row = conn.execute("""
            SELECT r.*, cd.contenido_html
            FROM registro_central r
            LEFT JOIN contenido_documento cd ON r.pk_registro_id = cd.fk_registro_id
            WHERE r.pk_registro_id = ?
        """, (registro_id,)).fetchone()

    if not row:
        flash("Documento no encontrado.", "danger")
        return redirect(url_for("documentos.listar"))

    d = dict(row)
    wordoc = DocxDocument()

    titulo = wordoc.add_heading(d.get("asunto_resumen", "Sin titulo"), 0)
    titulo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    meta = [
        ("Codigo", d.get("codigo_completo", "")),
        ("Fecha",  d.get("fecha_radicacion", "")),
        ("Area",   d.get("area", "")),
        ("Estado", d.get("estado", "")),
    ]
    for label, valor in meta:
        wordoc.add_paragraph(f"{label}: {valor}", style="Intense Quote")

    wordoc.add_paragraph("")  # separador

    html = d.get("contenido_html") or ""
    texto = re.sub(r"<[^<]+?>", "", html)
    texto = re.sub(r"&nbsp;", " ", texto)
    texto = re.sub(r"&[a-z]+;", "", texto)
    texto = re.sub(r"\s{2,}", " ", texto).strip()
    for linea in texto.split("\n"):
        if linea.strip():
            wordoc.add_paragraph(linea.strip())

    buf = BytesIO()
    wordoc.save(buf)
    buf.seek(0)

    nombre_archivo = secure_filename(f"{d.get('codigo_completo', str(registro_id))}.docx")
    return send_file(
        buf,
        as_attachment=True,
        download_name=nombre_archivo,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# ── Dashboard de estadísticas ─────────────────────────────────────
@docs_bp.route("/dashboard")
@login_requerido
def dashboard_documentos():
    """Dashboard con estadísticas de documentos."""
    hoy = date.today().isoformat()
    with db_connection(autocommit=False) as conn:
        row_stats = conn.execute("""
            SELECT
                COUNT(*)                                                              AS total,
                SUM(CASE WHEN estado='Borrador'    THEN 1 ELSE 0 END)                AS borradores,
                SUM(CASE WHEN estado='En_revision' THEN 1 ELSE 0 END)                AS en_revision,
                SUM(CASE WHEN estado='Aprobado'    THEN 1 ELSE 0 END)                AS aprobados,
                SUM(CASE WHEN fecha_vencimiento < ? AND estado NOT IN
                         ('Aprobado','Archivado') THEN 1 ELSE 0 END)                 AS vencidos
            FROM registro_central
        """, (hoy,)).fetchone()

        por_area = conn.execute("""
            SELECT area, COUNT(*) AS c
            FROM registro_central GROUP BY area ORDER BY c DESC
        """).fetchall()

        por_tipo = conn.execute("""
            SELECT tipo_documento, COUNT(*) AS c
            FROM registro_central GROUP BY tipo_documento ORDER BY c DESC LIMIT 10
        """).fetchall()

        tendencia = conn.execute("""
            SELECT strftime('%Y-%m', fecha_radicacion) AS mes, COUNT(*) AS c
            FROM registro_central
            WHERE fecha_radicacion IS NOT NULL
            GROUP BY mes ORDER BY mes ASC LIMIT 12
        """).fetchall()

    stats = dict(row_stats) if row_stats else {}
    return render_template("documentos/dashboard.html",
        stats=stats,
        por_area=[dict(r) for r in por_area],
        por_tipo=[dict(r) for r in por_tipo],
        tendencia=[dict(r) for r in tendencia],
    )


@docs_bp.route("/api/areas")
@login_requerido
def api_areas():
    """Lista áreas: primero BD, fallback a AREAS hardcodeado."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT codigo, nombre FROM areas WHERE activo=1 ORDER BY nombre"
        ).fetchall()
        if rows:
            return jsonify([dict(r) for r in rows])
    except Exception:
        pass
    finally:
        conn.close()
    return jsonify([{"codigo": c, "nombre": n} for c, n in AREAS])


@docs_bp.route("/api/ia_proxy", methods=["POST"])
@login_requerido
def api_ia_proxy():
    import requests as _req
    data        = request.get_json(silent=True) or {}
    instruccion = data.get("instruccion","").strip()
    contexto    = data.get("contexto","").strip()
    if not instruccion:
        return jsonify({"ok": False, "error": "Instruccion vacia"}), 400

    api_key       = ""
    proveedor     = "anthropic"
    ollama_url    = "http://localhost:11434"
    ollama_modelo = "llama3.2"

    conn_cfg = get_db()
    try:
        filas = {r["clave"]:r["valor"] for r in conn_cfg.execute(
            "SELECT clave,valor FROM configuracion WHERE clave IN (?,?,?,?)",
            ["anthropic_api_key","ollama_url","ollama_modelo","ia_proveedor"]
        ).fetchall()}
        prov_cfg  = filas.get("ia_proveedor","anthropic")
        clave_bd  = filas.get("anthropic_api_key","").strip()
        if prov_cfg == "ollama":
            proveedor     = "ollama"
            ollama_url    = filas.get("ollama_url","http://localhost:11434")
            ollama_modelo = filas.get("ollama_modelo","llama3.2")
        elif clave_bd and not clave_bd.startswith("sk-ant-DEMO"):
            api_key = clave_bd; proveedor = "anthropic"
        else:
            env_key = os.environ.get("ANTHROPIC_API_KEY","")
            if env_key: api_key = env_key; proveedor = "anthropic"
    except Exception:
        pass
    finally:
        conn_cfg.close()

    if proveedor == "anthropic" and not api_key:
        return jsonify({"ok": False, "error": "IA no configurada. Vaya a Admin > Configuracion > Modulo IA.",
                        "configurar_url": "/configuracion#ia-config-panel"}), 503

    prompt = (contexto + "\n\n" if contexto else "") + "INSTRUCCION: " + instruccion + "\n\nREGLAS: Tono formal colombiano. Sin markdown, texto plano. Max 400 palabras."

    if proveedor == "ollama":
        try:
            resp = _req.post(ollama_url + "/api/generate",
                             json={"model": ollama_modelo, "prompt": prompt, "stream": False}, timeout=60)
            if resp.status_code == 200:
                return jsonify({"ok": True, "texto": resp.json().get("response","").strip(), "proveedor": "ollama"})
            return jsonify({"ok": False, "error": "Ollama error " + str(resp.status_code),
                            "configurar_url": "/configuracion#ia-config-panel"}), 503
        except _req.exceptions.ConnectionError:
            return jsonify({"ok": False, "error": "Ollama no responde en " + ollama_url,
                            "configurar_url": "/configuracion#ia-config-panel"}), 503
        except Exception as e:
            return jsonify({"ok": False, "error": "Error Ollama: " + str(e)}), 503

    try:
        resp = _req.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 1000,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30)
        d = resp.json()
        if resp.status_code == 200:
            texto = "".join(b.get("text","") for b in d.get("content",[]) if b.get("type") == "text")
            return jsonify({"ok": True, "texto": texto, "proveedor": "anthropic"})
        elif resp.status_code == 401:
            return jsonify({"ok": False, "error": "Clave invalida. Actualicela en Admin > Configuracion.",
                            "configurar_url": "/configuracion#ia-config-panel"}), 401
        elif resp.status_code == 429:
            return jsonify({"ok": False, "error": "Limite API alcanzado. Espere un momento."}), 429
        else:
            return jsonify({"ok": False, "error": d.get("error",{}).get("message","Error API")}), resp.status_code
    except _req.exceptions.Timeout:
        return jsonify({"ok": False, "error": "IA tardo demasiado. Seleccione menos texto."}), 504
    except _req.exceptions.ConnectionError:
        return jsonify({"ok": False, "error": "Sin internet. Para IA offline configure Ollama."}), 503
    except Exception as e:
        return jsonify({"ok": False, "error": "Error: " + str(e)}), 503


# ── Versiones ────────────────────────────────────────────────────────
@docs_bp.route("/<int:registro_id>/versiones")
@login_requerido
def versiones(registro_id):
    conn = get_db()
    try:
        doc = conn.execute("SELECT pk_registro_id FROM registro_central WHERE pk_registro_id=?", (registro_id,)).fetchone()
        if not doc:
            return jsonify({"error": "No encontrado"}), 404
        rows = conn.execute("""
            SELECT version, fecha_edicion, editado_por,
                   SUBSTR(contenido_plain, 1, 200) as preview
            FROM contenido_documento WHERE fk_registro_id=?
            ORDER BY version DESC
        """, (registro_id,)).fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@docs_bp.route("/<int:registro_id>/restaurar/<int:version_num>", methods=["POST"])
@login_requerido
def restaurar_version(registro_id, version_num):
    conn = get_db()
    try:
        old = conn.execute("""
            SELECT contenido_html, contenido_plain
            FROM contenido_documento WHERE fk_registro_id=? AND version=?
        """, (registro_id, version_num)).fetchone()
        if not old:
            return jsonify({"error": "Version no encontrada"}), 404
        last_ver = conn.execute(
            "SELECT COALESCE(MAX(version),0) as m FROM contenido_documento WHERE fk_registro_id=?",
            (registro_id,)
        ).fetchone()["m"]
        new_ver = last_ver + 1
        conn.execute("""
            INSERT INTO contenido_documento
            (fk_registro_id, contenido_html, contenido_plain, version, editado_por)
            VALUES (?,?,?,?,?)
        """, (registro_id, old["contenido_html"], old["contenido_plain"],
              new_ver, session.get("nombre_usuario")))
        conn.commit()
        auditar(f"Documento {registro_id}: version {version_num} restaurada como v{new_ver}", modulo="documentos")
        return jsonify({"ok": True, "nueva_version": new_ver})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# ── Limpieza de borradores ───────────────────────────────────────────
@docs_bp.route("/limpiar_borradores", methods=["POST"])
@login_requerido
def limpiar_borradores_antiguos():
    if session.get("rol") != "admin":
        abort(403)
    conn = get_db()
    try:
        limite = (date.today() - timedelta(days=30)).isoformat()
        borradores = conn.execute("""
            SELECT pk_registro_id FROM registro_central
            WHERE estado='Borrador' AND fecha_radicacion < ?
        """, (limite,)).fetchall()
        if not borradores:
            flash("No hay borradores antiguos.", "info")
            return redirect(url_for("documentos.listar"))
        for b in borradores:
            bid = b["pk_registro_id"]
            for tabla, campo in [
                ("contenido_documento","fk_registro_id"),
                ("documento_firmantes","documento_id"),
                ("acciones_pendientes","fk_registro_id"),
                ("seguimiento_documento","fk_registro_id"),
                ("plazos_documento","fk_registro_id"),
                ("documentos_adjuntos","fk_registro_id"),
            ]:
                try:
                    conn.execute(f"DELETE FROM {tabla} WHERE {campo}=?", (bid,))
                except Exception:
                    pass
            conn.execute("DELETE FROM registro_central WHERE pk_registro_id=?", (bid,))
        conn.commit()
        flash(f"Se eliminaron {len(borradores)} borradores antiguos.", "success")
    except Exception as e:
        conn.rollback()
        _log_docs.error("limpiar_borradores: %s", e, exc_info=True)
        flash("Error al limpiar borradores. Contacte al administrador.", "danger")
    finally:
        conn.close()
    return redirect(url_for("documentos.listar"))


@docs_bp.route("/<int:registro_id>/desactivar_indicador", methods=["POST"])
@login_requerido
def desactivar_indicador(registro_id):
    conn = get_db()
    try:
        conn.execute("UPDATE registro_central SET indicador_activo=0 WHERE pk_registro_id=?", (registro_id,))
        conn.commit()
        flash("Indicador de plazo desactivado.", "info")
    except Exception as e:
        _log_docs.error("desactivar_indicador reg=%s: %s", registro_id, e, exc_info=True)
        flash("Error al desactivar el indicador. Contacte al administrador.", "danger")
    finally:
        conn.close()
    return redirect(url_for("documentos.ver", registro_id=registro_id))


# ════════════════════════════════════════════════════════════
# TRD — Archivo Total
# ════════════════════════════════════════════════════════════

@docs_bp.route("/api/clasificar", methods=["POST"])
@login_requerido
def api_clasificar():
    """Clasifica un documento según TRD determinística. No guarda nada."""
    if not CLASSIFIER_AVAILABLE:
        return jsonify({"ok": False, "error": "Clasificador no disponible"}), 503
    data   = request.get_json(silent=True) or {}
    tipo   = data.get("tipo_documento", "")
    asunto = data.get("asunto", "")
    area   = data.get("area", "")
    if not tipo and not asunto:
        return jsonify({"ok": False, "error": "tipo_documento o asunto requerido"}), 400
    clf = _clf_doc(tipo, asunto, area)
    return jsonify({"ok": True, "clasificacion": clf.to_dict()})


@docs_bp.route("/api/clasificar/<int:registro_id>", methods=["POST"])
@login_requerido
def api_clasificar_registro(registro_id):
    """Enriquece un registro existente con su clasificación TRD."""
    if not CLASSIFIER_AVAILABLE:
        return jsonify({"ok": False, "error": "Clasificador no disponible"}), 503
    conn = get_db()
    resultado = _enriquecer_registro(conn, registro_id)
    conn.close()
    return jsonify(resultado)


@docs_bp.route("/api/sugerir_expediente", methods=["POST"])
@login_requerido
def api_sugerir_expediente():
    """Sugiere expedientes existentes para vincular un documento."""
    data   = request.get_json(silent=True) or {}
    doc_id = data.get("documento_id", 0)
    asunto = data.get("asunto", "")
    from modules.documental.clasificador_documental import sugerir_expediente
    return jsonify(sugerir_expediente(doc_id, asunto))


@docs_bp.route("/api/alertas_trd")
@login_requerido
def alertas_trd():
    """Alertas TRD — usa gestor_trd si disponible. (#41: import consistente)"""
    if not _GESTOR_TRD_AVAILABLE:
        return jsonify({"ok": False, "error": "Módulo TRD no disponible"}), 503
    try:
        alertas = gestor_trd.verificar_transferencias_pendientes()
        return jsonify({"ok": True, "total_alertas": len(alertas),
                        "alertas": alertas, "fecha_consulta": datetime.now().isoformat()})
    except Exception as e:
        _log_docs.error("alertas_trd: %s", e, exc_info=True)
        return jsonify({"ok": False, "error": "Error al consultar alertas TRD"}), 500


@docs_bp.route("/api/trd/simular")
@login_requerido
def trd_simular():
    if not _GESTOR_TRD_AVAILABLE:
        return jsonify({"ok": False, "error": "Módulo TRD no disponible"}), 503
    try:
        return jsonify(gestor_trd.simular_transferencia())
    except Exception as e:
        _log_docs.error("trd_simular: %s", e, exc_info=True)
        return jsonify({"ok": False, "error": "Error al simular transferencia"}), 500


@docs_bp.route("/api/trd/solicitar_confirmacion", methods=["POST"])
@login_requerido
def trd_solicitar_confirmacion():
    if not _GESTOR_TRD_AVAILABLE:
        return jsonify({"ok": False, "error": "Módulo TRD no disponible"}), 503
    try:
        sim = gestor_trd.simular_transferencia()
    except Exception as e:
        _log_docs.error("trd_solicitar_confirmacion: %s", e, exc_info=True)
        return jsonify({"ok": False, "error": "Error al simular transferencia"}), 500
    if sim.get("total", 0) == 0:
        return jsonify({"ok": False, "mensaje": "No hay documentos pendientes de transferencia."})
    token = secrets.token_urlsafe(32)
    session["trd_confirm_token"] = token
    return jsonify({"ok": True, "simulacion": sim, "confirmacion_token": token,
                    "mensaje": f"Se procesarán {sim['total']} documentos. ¿Desea continuar?"})


@docs_bp.route("/api/transferir", methods=["POST"])
@login_requerido
def transferir_documentos():
    if not _GESTOR_TRD_AVAILABLE:
        return jsonify({"ok": False, "error": "Módulo TRD no disponible"}), 503
    data  = request.get_json() or {}
    token = data.get("confirmacion_token")
    if token and token != session.get("trd_confirm_token"):
        return jsonify({"ok": False, "error": "Token de confirmación inválido"}), 403
    session.pop("trd_confirm_token", None)
    try:
        resultado = gestor_trd.ejecutar_transferencias(usuario=session.get("nombre_usuario", "admin"))
    except Exception as e:
        _log_docs.error("transferir_documentos: %s", e, exc_info=True)
        return jsonify({"ok": False, "error": "Error al ejecutar transferencias"}), 500
    if resultado["ok"]:
        flash(f"Transferencia TRD completada: {resultado['total']} documentos procesados.", "success")
    else:
        flash("Error en transferencia TRD. Revise los logs.", "danger")
    return jsonify(resultado)


# ════════════════════════════════════════════════════════════
# SEMAFORO LEGAL
# ════════════════════════════════════════════════════════════

PLAZOS_CPACA = {"PQR": 15, "REQ": 30, "RECURSO": 30, "GENERAL": 60}

@docs_bp.route("/api/indicador_tiempo/<int:doc_id>")
@login_requerido
def indicador_tiempo(doc_id):
    conn = None
    try:
        conn = get_db()
        doc = conn.execute("""
            SELECT r.fecha_radicacion, r.tipo_documento, r.fase_archivo,
                   t.anos_gestion, t.anos_central, t.disposicion_final
            FROM registro_central r
            LEFT JOIN trd t ON r.fk_trd_id = t.pk_trd_id
            WHERE r.pk_registro_id = ?
        """, (doc_id,)).fetchone()
        if not doc:
            return jsonify({"error": "Documento no encontrado"}), 404

        try:
            fecha_rad = datetime.strptime(doc["fecha_radicacion"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return jsonify({"error": "Fecha invalida"}), 400

        hoy      = date.today()
        tipo_doc = (doc["tipo_documento"] or "").upper()

        if any(x in tipo_doc for x in ["PQR","REQ","RECURSO"]):
            dias_plazo = PLAZOS_CPACA.get("PQR" if "PQR" in tipo_doc else "REQ", 15)
            try:
                from core.calendario_colombiano import calcular_fecha_habil
                fecha_venc = calcular_fecha_habil(fecha_rad, dias_plazo)
            except ImportError:
                fecha_venc = fecha_rad + timedelta(days=int(dias_plazo * 1.4))
            dias_r = (fecha_venc - hoy).days
            if dias_r > 5:    color, texto = "success", f"{dias_r} dias habiles"
            elif dias_r >= 0: color, texto = "warning", f"Urgente! {dias_r} dias"
            else:              color, texto = "danger",  f"Vencido hace {abs(dias_r)} dias"
            return jsonify({"tipo_calculo": f"CPACA ({dias_plazo} dias habiles)",
                            "dias_restantes": dias_r, "fecha_vencimiento": fecha_venc.isoformat(),
                            "semaforo": color, "texto_badge": texto})

        anos = doc.get("anos_gestion") or 2
        try:
            fecha_venc = fecha_rad.replace(year=fecha_rad.year + int(anos))
        except ValueError:
            fecha_venc = fecha_rad + timedelta(days=int(anos)*365)
        dias_r = (fecha_venc - hoy).days
        if dias_r > 60:    color, texto = "success", f"{dias_r} dias en Gestion"
        elif dias_r >= 0:  color, texto = "warning", f"{dias_r} dias restantes"
        else:              color, texto = "danger",  "Transferencia requerida"
        return jsonify({"tipo_calculo": f"TRD - Gestion ({anos} anos)",
                        "dias_restantes": dias_r, "fecha_vencimiento": fecha_venc.isoformat(),
                        "semaforo": color, "texto_badge": texto})
    finally:
        if conn: conn.close()


# ════════════════════════════════════════════════════════════
# VISTA PREVIA TEMPORAL
# ════════════════════════════════════════════════════════════

@docs_bp.route("/documento/vista_previa_temporal", methods=["POST"])
@login_requerido
def vista_previa_temporal():
    # CSRF obligatorio en rutas POST que consumen recursos (#7)
    if not verificar_token_csrf():
        flash("Token de seguridad inválido. Recargue la página.", "danger")
        return redirect(url_for("documentos.listar"))

    try:
        from weasyprint import HTML
    except ImportError:
        flash("WeasyPrint no instalado. pip install weasyprint", "warning")
        return redirect(url_for("documentos.listar"))

    area           = request.form.get("area","N/A")
    tipo           = request.form.get("tipo_documento","N/A")
    asunto         = request.form.get("asunto_resumen","Sin Asunto")
    notas          = request.form.get("notas_internas","")
    fecha_rad      = request.form.get("fecha_radicacion", date.today().isoformat())
    contenido_html = request.form.get("contenido_html","")
    destinatario   = request.form.get("fk_contacto_id","")

    nombre_contacto = ""
    conn = get_db()
    if destinatario:
        row = conn.execute("SELECT razon_social FROM contactos WHERE pk_contacto_id=?", (destinatario,)).fetchone()
        nombre_contacto = row["razon_social"] if row else ""
    nombre_entidad = conn.execute("SELECT valor FROM configuracion WHERE clave='nombre_acueducto'").fetchone()
    nombre_entidad = nombre_entidad["valor"] if nombre_entidad else "Acueducto"
    slogan = conn.execute("SELECT valor FROM configuracion WHERE clave='eslogan'").fetchone()
    slogan = slogan["valor"] if slogan else "Sistema de Gestion Documental"
    conn.close()

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
    <style>body{{font-family:Arial;margin:2cm;color:#333;}}
    .wm{{position:absolute;top:40%;left:5%;transform:rotate(-35deg);font-size:60px;color:rgba(220,53,69,.12);font-weight:bold;}}
    .hdr{{text-align:center;border-bottom:2px solid #1E3A8A;padding-bottom:12px;margin-bottom:20px;}}
    table{{width:100%;border-collapse:collapse;margin-bottom:20px;}}
    td{{padding:6px;border:1px solid #e2e8f0;}} .lbl{{background:#f8fafc;font-weight:bold;width:25%;}}
    .box{{border:1px solid #cbd5e1;padding:16px;min-height:120px;}}
    </style></head><body>
    <div class="wm">VISTA PREVIA SIN RADICAR</div>
    <div class="hdr"><b style="color:#1E3A8A;font-size:16px;">{nombre_entidad}</b>
    <br><span style="font-size:12px;color:#64748b;">{slogan}</span></div>
    <table><tr><td class="lbl">Area:</td><td>{area}</td><td class="lbl">Fecha:</td><td>{fecha_rad}</td></tr>
    <tr><td class="lbl">Tipo:</td><td>{tipo}</td><td class="lbl">Destinatario:</td><td>{nombre_contacto or 'N/A'}</td></tr>
    <tr><td class="lbl">Elaborado por:</td><td>{session.get("nombre_usuario","Usuario")}</td>
    <td class="lbl">Estado:</td><td>Borrador (sin radicar)</td></tr></table>
    <h3>Asunto:</h3><div class="box">{asunto.replace(chr(10),"<br>")}</div>
    {"<h3>Contenido:</h3><div class='box'>"+contenido_html+"</div>" if contenido_html else ""}
    {"<h3>Notas internas:</h3><div class='box' style='background:#fffbeb;'>"+notas.replace(chr(10),"<br>")+"</div>" if notas else ""}
    <hr><p style="font-size:10px;text-align:center;color:#888;">
    Vista previa sin validez oficial. Radique el documento para que tenga efecto legal.</p>
    </body></html>"""
    # tempfile.NamedTemporaryFile evita colisión entre usuarios y /tmp desbordado (#3)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix="vprevia_") as tmp:
        tmp_path = tmp.name
    try:
        HTML(string=html).write_pdf(tmp_path)
        return send_file(tmp_path, mimetype="application/pdf")
    finally:
        # Limpieza garantizada al salir del request
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ════════════════════════════════════════════════════════════
# EXPEDIENTES — Hoja de Control AGN
# ════════════════════════════════════════════════════════════

@docs_bp.route("/api/expediente", methods=["POST"])
@login_requerido
def crear_expediente():
    data = request.get_json() or {}
    if not data.get("nombre") or not data.get("codigo"):
        return jsonify({"ok": False, "error": "Codigo y nombre requeridos"}), 400
    conn = get_db()
    try:
        cur = conn.execute("""INSERT INTO expedientes (codigo_expediente,nombre,descripcion,responsable_id)
            VALUES (?,?,?,?)""", (data["codigo"],data["nombre"],data.get("descripcion",""),data.get("responsable_id")))
        conn.commit()
        return jsonify({"ok": True, "id": cur.lastrowid})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@docs_bp.route("/api/expediente/<int:exp_id>/documentos", methods=["POST"])
@login_requerido
def asignar_documento_expediente(exp_id):
    data      = request.get_json() or {}
    doc_id    = data.get("documento_id")
    folio_ini = data.get("folio_inicio")
    folio_fin = data.get("folio_fin")
    if not doc_id:
        return jsonify({"ok": False, "error": "documento_id requerido"}), 400
    conn = get_db()
    try:
        conn.execute("UPDATE registro_central SET fk_expediente_id=?,folio_inicio=?,folio_fin=? WHERE pk_registro_id=?",
                     (exp_id, folio_ini, folio_fin, doc_id))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@docs_bp.route("/expediente/<int:exp_id>/hoja_control")
@login_requerido
def hoja_control_expediente(exp_id):
    try:
        from weasyprint import HTML
    except ImportError:
        flash("WeasyPrint no instalado.", "warning")
        return redirect(url_for("documentos.listar"))

    conn = None
    try:
        conn = get_db()
        exp  = conn.execute("SELECT * FROM expedientes WHERE pk_expediente_id=?", (exp_id,)).fetchone()
        if not exp:
            flash("Expediente no encontrado", "danger")
            return redirect(url_for("documentos.listar"))

        docs = conn.execute("""SELECT codigo_completo,asunto_resumen,fecha_radicacion,
            folio_inicio,folio_fin,tipo_documento FROM registro_central
            WHERE fk_expediente_id=? ORDER BY folio_inicio""", (exp_id,)).fetchall()

        total_folios = sum((d["folio_fin"]-d["folio_inicio"]+1)
                           for d in docs if d["folio_inicio"] and d["folio_fin"])
        filas = ""
        for d in docs:
            rango = f"{d['folio_inicio']} - {d['folio_fin']}" if d["folio_inicio"] and d["folio_fin"] else "Sin folio"
            filas += f"<tr><td>{rango}</td><td>{d['codigo_completo']}</td><td>{d['tipo_documento'] or 'N/A'}</td><td>{d['asunto_resumen'][:50]}</td><td>{d['fecha_radicacion']}</td></tr>"

        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
        <style>body{{font-family:Arial;margin:2cm;}} h1{{text-align:center;}}
        table{{width:100%;border-collapse:collapse;margin-top:16px;}}
        th,td{{border:1px solid #333;padding:7px;text-align:left;}}
        th{{background:#1E3A8A;color:white;}} .alerta{{color:red;font-weight:bold;}}</style>
        </head><body>
        <h1>Hoja de Control de Expediente</h1>
        <p><strong>Codigo:</strong> {exp['codigo_expediente']}<br>
        <strong>Nombre:</strong> {exp['nombre']}<br>
        <strong>Descripcion:</strong> {exp['descripcion'] or ''}<br>
        <strong>Fecha apertura:</strong> {exp['fecha_apertura']}<br>
        <strong>Total folios:</strong> {total_folios}</p>
        {"<p class='alerta'>ATENCION: Expediente supera los 200 folios maximos (AGN - Acuerdo 038/2002)</p>" if total_folios > 200 else ""}
        <table><thead><tr><th>Folio(s)</th><th>Codigo</th><th>Tipo</th><th>Asunto</th><th>Fecha</th></tr></thead>
        <tbody>{filas}</tbody></table>
        <p style="margin-top:30px;font-size:10px;color:#888;">
        Hoja de Control generada por PARAGUASMJ</p>
        </body></html>"""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix=f"hoja_ctrl_{exp_id}_") as tmp:
            tmp_path = tmp.name
        try:
            HTML(string=html).write_pdf(tmp_path)
            return send_file(tmp_path, as_attachment=True,
                             download_name=f"Hoja_Control_{exp['codigo_expediente']}.pdf",
                             mimetype="application/pdf")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    finally:
        if conn: conn.close()


# ════════════════════════════════════════════════════════════
# FIRMA CRIPTOGRAFICA
# ════════════════════════════════════════════════════════════

@docs_bp.route("/api/firmar", methods=["POST"])
@login_requerido
@limitar("api_firmar", max_attempts=5, window_seconds=60,
         mensaje="Demasiados intentos de firma. Espere 1 minuto.")
def api_firmar():
    data        = request.get_json() or {}
    doc_id      = data.get("documento_id")
    firmante_id = data.get("firmante_id")
    if not doc_id or not firmante_id:
        return jsonify({"ok": False, "error": "documento_id y firmante_id requeridos"}), 400

    conn = get_db()
    try:
        asig = conn.execute("SELECT id,estado FROM documento_firmantes WHERE documento_id=? AND firmante_id=?",
                            (doc_id, firmante_id)).fetchone()
        if not asig:
            return jsonify({"ok": False, "error": "Firmante no asignado a este documento"}), 400
        if asig["estado"] == "firmado":
            return jsonify({"ok": False, "error": "Ya fue firmado por este usuario"}), 400

        firmante = conn.execute("SELECT nombre_completo,cargo FROM firmantes WHERE pk_firmante_id=?", (firmante_id,)).fetchone()
        doc      = conn.execute("SELECT codigo_completo FROM registro_central WHERE pk_registro_id=?", (doc_id,)).fetchone()

        ts = SaneadorForense.normalizar_fecha_estatica(datetime.now())
        ip = SaneadorForense.obtener_ip_segura(request)

        # Hash del contenido del documento — ancla la firma al contenido exacto (#4)
        contenido_row = conn.execute(
            "SELECT contenido_html FROM contenido_documento WHERE fk_registro_id=? ORDER BY version DESC LIMIT 1",
            (doc_id,)
        ).fetchone()
        contenido_hash = hashlib.sha256(
            (contenido_row["contenido_html"] or "").encode("utf-8")
        ).hexdigest() if contenido_row else "sin_contenido"

        # Payload incluye hash del contenido: la firma queda anclada al documento exacto
        payload    = f"{contenido_hash}|{doc['codigo_completo']}|{firmante_id}|{ts}|{ip}"
        hash_firma = hashlib.sha256(payload.encode()).hexdigest()

        conn.execute("UPDATE documento_firmantes SET estado='firmado',fecha_firma=?,hash_firma=?,ip_firma=? WHERE id=?",
                     (ts, hash_firma, ip, asig["id"]))
        conn.execute("INSERT INTO seguimiento_documento (fk_registro_id,estado_actual,usuario,observaciones) VALUES (?,?,?,?)",
                     (doc_id, "Firmado", session.get("nombre_usuario"),
                      f"Firma: {firmante['nombre_completo']} - Hash: {hash_firma[:12]}..."))

        pendientes = conn.execute("SELECT COUNT(*) FROM documento_firmantes WHERE documento_id=? AND estado='pendiente'", (doc_id,)).fetchone()[0]
        if pendientes == 0:
            conn.execute("UPDATE registro_central SET estado='Aprobado' WHERE pk_registro_id=?", (doc_id,))
            conn.execute("INSERT INTO seguimiento_documento (fk_registro_id,estado_actual,usuario,observaciones) VALUES (?,?,?,?)",
                         (doc_id, "Aprobado", "Sistema", "Documento aprobado - todas las firmas completadas"))

        conn.commit()
        auditar(f"Firma: {doc['codigo_completo']} por {firmante['nombre_completo']}", modulo="documentos")
        return jsonify({"ok": True, "hash": hash_firma, "timestamp": ts})
    except Exception as e:
        conn.rollback()
        _log_docs.error("api_firmar doc=%s firmante=%s: %s", doc_id, firmante_id, e, exc_info=True)
        return jsonify({"ok": False, "error": "Error al registrar la firma. Contacte al administrador."}), 500
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════
# FORMATO DE TRANSFERENCIA
# ════════════════════════════════════════════════════════════

@docs_bp.route("/formato_transferencia/<fase_origen>")
@login_requerido
def formato_transferencia(fase_origen):
    """Exporta inventario de transferencia en Excel usando openpyxl directo — sin pandas (#10)."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        flash("openpyxl no instalado. pip install openpyxl", "warning")
        return redirect(url_for("documentos.listar"))

    conn = get_db()
    docs = conn.execute("""
        SELECT r.codigo_completo, r.asunto_resumen, r.fecha_radicacion,
               r.fecha_ingreso_fase, t.nombre AS serie_nombre, t.disposicion_final
        FROM registro_central r
        LEFT JOIN trd t ON r.fk_trd_id = t.pk_trd_id
        WHERE r.fase_archivo = ?
        ORDER BY r.fecha_radicacion
    """, (fase_origen,)).fetchall()
    conn.close()
    if not docs:
        flash("No hay documentos en esta fase.", "warning")
        return redirect(url_for("documentos.listar"))

    wb = Workbook()
    ws = wb.active
    ws.title = f"Inventario_{fase_origen}"[:31]

    # Encabezado con estilo
    encabezados = ["Código", "Asunto / Resumen", "Fecha Radicación",
                   "Ingreso Fase", "Serie Documental", "Disposición Final"]
    hdr_fill = PatternFill("solid", fgColor="1E3A8A")
    hdr_font = Font(bold=True, color="FFFFFF")
    for col, titulo in enumerate(encabezados, 1):
        cell = ws.cell(row=1, column=col, value=titulo)
        cell.fill = hdr_fill
        cell.font = hdr_font
        cell.alignment = Alignment(horizontal="center")

    for row_num, d in enumerate(docs, 2):
        ws.cell(row=row_num, column=1, value=d["codigo_completo"])
        ws.cell(row=row_num, column=2, value=d["asunto_resumen"])
        ws.cell(row=row_num, column=3, value=d["fecha_radicacion"])
        ws.cell(row=row_num, column=4, value=d["fecha_ingreso_fase"])
        ws.cell(row=row_num, column=5, value=d["serie_nombre"] or "Sin clasificar")
        ws.cell(row=row_num, column=6, value=d["disposicion_final"] or "")

    # Ancho automático aproximado
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f"Formato_Transferencia_{fase_origen}_{date.today()}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@docs_bp.route("/api/indice/stats")
@login_requerido
def api_indice_stats():
    """Estadísticas del índice maestro de expedientes (#9)."""
    from modules.indexer import estadisticas_indice
    conn = get_db()
    resultado = estadisticas_indice(conn)
    conn.close()
    return jsonify(resultado)


@docs_bp.route("/api/indice/expediente/<int:exp_id>")
@login_requerido
def api_indice_expediente(exp_id):
    """Índice completo de un expediente con todos sus documentos (#9)."""
    from modules.indexer import indice_expediente
    conn = get_db()
    resultado = indice_expediente(conn, exp_id)
    conn.close()
    return jsonify(resultado)


@docs_bp.route("/api/indice/buscar")
@login_requerido
def api_indice_buscar():
    """Búsqueda en expedientes por código, nombre o descripción (#9)."""
    from modules.indexer import buscar_en_expedientes
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify({"ok": False, "error": "Mínimo 2 caracteres"}), 400
    conn = get_db()
    resultados = buscar_en_expedientes(conn, q)
    conn.close()
    return jsonify({"ok": True, "resultados": resultados, "total": len(resultados)})


@docs_bp.route("/api/guardar_config_tipos", methods=["POST"])
@login_requerido
def guardar_config_tipos():
    if session.get("rol") != "admin":
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json() or {}
    if "tipos" not in data:
        return jsonify({"error": "Datos invalidos"}), 400
    conn = get_db()
    try:
        conn.execute("DELETE FROM tipos_documento")
        for t in data["tipos"]:
            conn.execute("INSERT INTO tipos_documento (codigo, nombre, activo) VALUES (?,?,?)",
                (t["codigo"], t["nombre"], 1 if t.get("activo", True) else 0))
        conn.commit()
        auditar("Tipos de documento actualizados", modulo="configuracion")
        return jsonify({"ok": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@docs_bp.route("/expedientes")
@login_requerido
def listar_expedientes():
    conn = None
    try:
        conn = get_db()
        expedientes = conn.execute("""
            SELECT e.*,
                   (SELECT COUNT(*) FROM registro_central
                    WHERE fk_expediente_id = e.pk_expediente_id) as total_documentos,
                   (SELECT MIN(fecha_radicacion) FROM registro_central
                    WHERE fk_expediente_id = e.pk_expediente_id) as fecha_inicio,
                   (SELECT MAX(fecha_radicacion) FROM registro_central
                    WHERE fk_expediente_id = e.pk_expediente_id) as fecha_fin
            FROM expedientes e
            ORDER BY e.fecha_apertura DESC
        """).fetchall()
        return render_template("documentos/expedientes.html",
                               expedientes=[dict(e) for e in expedientes])
    finally:
        if conn: conn.close()
