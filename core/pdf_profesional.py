"""
core/pdf_profesional.py
Generacion de PDFs profesionales con ReportLab.
Mejora estetica segun PROGRAMA_1.doc y PROGRAMA_2.doc:
  - Membrete institucional con logo, eslogan, NIT
  - Margenes A4: 2.5cm sup, 2cm lados, 2cm inf
  - Tipografia jerarquica (titulo, subtitulos, cuerpo, tablas)
  - Numeracion automatica de paginas (X/Y)
  - Soporte para actas de entrega de materiales con totales
  - Soporte para contestacion a requerimiento fiscal
  - Plantilla generica para cualquier documento institucional
"""
import os, re, logging
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.pdfgen import canvas as rl_canvas
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from core.database_manager import get_db

logger = logging.getLogger("asuacap.pdf")

# Colores institucionales
C_AZUL    = colors.HexColor("#1E3A8A")
C_VERDE   = colors.HexColor("#0F6E56")
C_AGUA    = colors.HexColor("#0ea5e9")
C_GRIS    = colors.HexColor("#64748B")
C_GRISLT  = colors.HexColor("#F1F5F9")
C_SEP     = colors.HexColor("#2C7DA0")

W, H = A4
MARGEN_IZQ = 2.0*cm
MARGEN_DER = 2.0*cm
MARGEN_SUP = 2.5*cm
MARGEN_INF = 2.0*cm


def _html_plain(html: str) -> str:
    texto = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    texto = re.sub(r"</p>", "\n\n", texto, flags=re.IGNORECASE)
    texto = re.sub(r"<[^<]+?>", "", texto)
    return texto.replace("&nbsp;","  ").replace("&amp;","&").replace("&lt;","<").replace("&gt;",">").strip()


def _obtener_cfg() -> dict:
    """Lee la configuracion institucional desde la BD."""
    try:
        conn = get_db()
        rows = conn.execute("SELECT clave, valor FROM configuracion WHERE categoria='Institucional'").fetchall()
        conn.close()
        return {r["clave"]: r["valor"] for r in rows}
    except Exception:
        return {}


class NumPaginasCanvas(rl_canvas.Canvas):
    """Canvas que imprime 'Pagina X de Y' en el pie."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_pie(num_pages)
            super().showPage()
        super().save()

    def _draw_pie(self, total):
        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(C_GRIS)
        texto_pie = f"Sistema PARAGUASMJ — Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        texto_pag = f"Página {self._pageNumber} de {total}"
        y = MARGEN_INF * 0.5
        self.drawString(MARGEN_IZQ, y, texto_pie)
        self.drawRightString(W - MARGEN_DER, y, texto_pag)
        # Linea separadora pie
        self.setStrokeColor(C_SEP)
        self.setLineWidth(0.5)
        self.line(MARGEN_IZQ, y + 4*mm, W - MARGEN_DER, y + 4*mm)
        self.restoreState()


def _membrete(story, cfg: dict, tipo_doc: str, codigo: str,
              fecha_doc: str, destinatario: str = ""):
    """Construye el membrete institucional (cabecera del documento)."""

    styles = getSampleStyleSheet()
    nombre_asoc = cfg.get("nombre_completo",
        "ASOCIACION DE SUSCRIPTORES DEL ACUEDUCTO COMUNITARIO EL PUENTE - ASUACAP").upper()
    nit      = cfg.get("nit", "832.001.389-2")
    municipio= cfg.get("municipio","Villeta, Cundinamarca")
    correo   = cfg.get("correo_oficial","aacueductoelpuente@yahoo.com")
    eslogan  = "Gestion comunitaria para el agua y el desarrollo sostenible"

    est_nombre = ParagraphStyle("nombre",fontName="Helvetica-Bold",fontSize=12,
                                 textColor=C_AZUL,alignment=TA_CENTER,leading=14)
    est_eslogan= ParagraphStyle("eslogan",fontName="Helvetica-Oblique",fontSize=8,
                                 textColor=C_GRIS,alignment=TA_CENTER)
    est_datos  = ParagraphStyle("datos",  fontName="Helvetica",fontSize=8,
                                 textColor=C_GRIS,alignment=TA_CENTER)

    # Tabla del membrete (logo | datos institucionales)
    datos_institucional = [
        Paragraph(nombre_asoc, est_nombre),
        Spacer(1, 2),
        Paragraph(f'"{eslogan}"', est_eslogan),
        Spacer(1, 2),
        Paragraph(f"NIT {nit} | {municipio} | {correo}", est_datos),
    ]
    col_datos = W - MARGEN_IZQ - MARGEN_DER
    tabla_header = Table([[datos_institucional]], colWidths=[col_datos])
    tabla_header.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    story.append(tabla_header)

    # Linea separadora azul
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=2.5, color=C_SEP, spaceAfter=10))

    # Tipo de documento y metadatos
    est_tipo = ParagraphStyle("tipo",fontName="Helvetica-Bold",fontSize=11,
                               textColor=C_BLANCO if False else C_AZUL,alignment=TA_LEFT)
    est_meta = ParagraphStyle("meta",fontName="Helvetica",fontSize=9,
                               textColor=colors.black,alignment=TA_LEFT)

    meta_data = [
        ["Tipo de documento:", tipo_doc],
        ["Código:",            codigo],
        ["Fecha:",             fecha_doc],
    ]
    if destinatario:
        meta_data.append(["Destinatario:", destinatario])

    col_w = [col_datos*0.3, col_datos*0.7]
    tabla_meta = Table(meta_data, colWidths=col_w)
    tabla_meta.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (0,-1), C_GRISLT),
        ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",    (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE",    (0,0), (-1,-1), 9.5),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ("PADDING",     (0,0), (-1,-1), 5),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(tabla_meta)
    story.append(Spacer(1, 12))


def generar_pdf_documento(registro_id: int) -> str | None:
    """
    Genera PDF profesional de un documento del registro central.
    Usa configuracion institucional desde BD.
    Retorna ruta del PDF generado.
    """
    conn = get_db()
    try:
        doc = conn.execute("""
            SELECT r.*, c.razon_social as contacto_nombre
            FROM registro_central r
            LEFT JOIN contactos c ON r.fk_contacto_id=c.pk_contacto_id
            WHERE r.pk_registro_id=?
        """, (registro_id,)).fetchone()
        if not doc:
            return None

        contenido_row = conn.execute(
            "SELECT contenido_html FROM contenido_documento WHERE fk_registro_id=?",
            (registro_id,)
        ).fetchone()

        firmantes_aprobados = conn.execute("""
            SELECT f.nombre_completo, f.cargo, o.fecha_aprobacion
            FROM autorizaciones_otp o
            JOIN firmantes f ON o.fk_firmante_id=f.pk_firmante_id
            WHERE o.fk_registro_id=? AND o.estado='Aprobado'
            ORDER BY o.fecha_aprobacion
        """, (registro_id,)).fetchall()

        cfg = _obtener_cfg()

        os.makedirs(Config.PDF_FOLDER, exist_ok=True)
        pdf_path = os.path.join(Config.PDF_FOLDER, f"{doc['codigo_completo'].replace('/','_')}.pdf")

        # ── Estilos ────────────────────────────────────────────────
        styles = getSampleStyleSheet()
        est_h2 = ParagraphStyle("h2",fontName="Helvetica-Bold",fontSize=12,
                                 textColor=C_AZUL,spaceBefore=16,spaceAfter=6,
                                 borderPad=0,leading=14)
        est_h3 = ParagraphStyle("h3",fontName="Helvetica-Bold",fontSize=11,
                                 textColor=C_SEP,spaceBefore=12,spaceAfter=4)
        est_body= ParagraphStyle("body",fontName="Helvetica",fontSize=10,
                                  leading=14,spaceBefore=4,spaceAfter=4,
                                  alignment=TA_JUSTIFY)
        est_firma=ParagraphStyle("firma",fontName="Helvetica",fontSize=9,
                                  alignment=TA_CENTER)

        story = []

        # Membrete
        _membrete_logo(story, cfg, Config.DB_PATH,
                  tipo_doc=doc["tipo_documento"],
                  codigo=doc["codigo_completo"],
                  fecha_doc=doc["fecha_radicacion"],
                  destinatario=doc.get("contacto_nombre") or "")

        # Asunto
        story.append(Paragraph(f"<b>ASUNTO:</b> {doc['asunto_resumen']}", est_body))
        story.append(Spacer(1, 10))

        # Contenido
        if contenido_row and contenido_row["contenido_html"]:
            texto = _html_plain(contenido_row["contenido_html"])
            for parr in texto.split("\n\n"):
                if parr.strip():
                    story.append(Paragraph(parr.strip(), est_body))
        else:
            story.append(Paragraph("[Sin contenido redactado]", est_body))

        # Firmas
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=0.5, color=C_GRIS))
        story.append(Spacer(1, 10))

        if firmantes_aprobados:
            firmas_data = [[
                Paragraph(
                    f"_____________________________<br/><b>{f['nombre_completo']}</b><br/>"
                    f"{f['cargo']}<br/>"
                    f"<font size=8 color='#64748B'>Aprobado: {(f['fecha_aprobacion'] or '')[:10]}</font>",
                    est_firma)
                for f in firmantes_aprobados
            ]]
        else:
            rep   = cfg.get("representante_legal","Jose H. Ramirez")
            cargo = cfg.get("cargo_representante","Presidente")
            firmas_data = [[
                Paragraph(f"_____________________________<br/><b>{rep}</b><br/>{cargo}", est_firma)
            ]]

        t_firmas = Table(firmas_data, colWidths=[None]*len(firmas_data[0]))
        t_firmas.setStyle(TableStyle([
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("VALIGN",(0,0),(-1,-1),"BOTTOM"),
        ]))
        story.append(t_firmas)

        # Generar PDF con numeracion
        buf = BytesIO()
        doc_pdf = SimpleDocTemplate(buf, pagesize=A4,
            leftMargin=MARGEN_IZQ, rightMargin=MARGEN_DER,
            topMargin=MARGEN_SUP,  bottomMargin=MARGEN_INF+1*cm)
        doc_pdf.build(story, canvasmaker=NumPaginasCanvas)

        with open(pdf_path, 'wb') as f:
            f.write(buf.getvalue())

        # Actualizar ruta en BD
        conn2 = get_db()
        conn2.execute("UPDATE registro_central SET ruta_archivo_pdf=? WHERE pk_registro_id=?",
                      (pdf_path, registro_id))
        conn2.commit(); conn2.close()

        logger.info(f"PDF generado: {pdf_path}")
        return pdf_path

    except Exception as e:
        logger.error(f"Error PDF doc {registro_id}: {e}")
        return None
    finally:
        conn.close()


def generar_acta_entrega_materiales(orden_compra_id: int) -> str | None:
    """
    Genera acta de entrega de materiales a partir de una OC.
    Estructura: encabezado, tabla de materiales con totales, declaracion, firmas.
    """
    conn = get_db()
    try:
        oc = conn.execute("""
            SELECT r.codigo_completo, r.fecha_radicacion, r.asunto_resumen,
                   c.razon_social as proveedor
            FROM registro_central r
            LEFT JOIN contactos c ON r.fk_contacto_id=c.pk_contacto_id
            WHERE r.pk_registro_id=?
        """, (orden_compra_id,)).fetchone()
        if not oc:
            return None

        items = conn.execute("""
            SELECT descripcion, unidad, cantidad, precio_unitario, subtotal, iva_porcentaje
            FROM ordenes_compra_productos
            WHERE fk_registro_id=?
        """, (orden_compra_id,)).fetchall()

        cfg = _obtener_cfg()
        styles = getSampleStyleSheet()
        est_body = ParagraphStyle("body",fontName="Helvetica",fontSize=10,leading=14,
                                   spaceBefore=4,spaceAfter=4,alignment=TA_JUSTIFY)
        est_firma= ParagraphStyle("firma",fontName="Helvetica",fontSize=9,alignment=TA_CENTER)

        story = []
        _membrete_logo(story, cfg, Config.DB_PATH,
                  tipo_doc="ACTA DE ENTREGA DE MATERIALES",
                  codigo=f"ACTA-{oc['codigo_completo']}",
                  fecha_doc=oc["fecha_radicacion"])

        story.append(Paragraph(
            f"<b>Orden de Compra de referencia:</b> {oc['codigo_completo']}", est_body))
        story.append(Paragraph(
            f"<b>Proveedor:</b> {oc['proveedor'] or 'N/A'}", est_body))
        story.append(Spacer(1, 10))

        # Tabla de materiales
        hdrs = [["N°","Descripción","Unidad","Cantidad","Precio Unit.","Subtotal"]]
        filas = hdrs
        total = 0.0
        for i, item in enumerate(items, 1):
            filas.append([
                str(i), item["descripcion"], item["unidad"],
                f"{item['cantidad']:.2f}",
                f"${item['precio_unitario']:,.0f}",
                f"${item['subtotal']:,.0f}"
            ])
            total += float(item["subtotal"])
        filas.append(["","","","","<b>TOTAL:</b>",f"<b>${total:,.0f}</b>"])

        tabla_items = Table(filas, colWidths=[
            1.2*cm, 6.5*cm, 1.8*cm, 2*cm, 2.8*cm, 2.8*cm])
        tabla_items.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0), C_AZUL),
            ("TEXTCOLOR", (0,0),(-1,0), colors.white),
            ("FONTNAME",  (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",  (0,0),(-1,-1), 9),
            ("GRID",      (0,0),(-1,-1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS",(0,1),(-1,-2),[colors.white, C_GRISLT]),
            ("BACKGROUND",(0,-1),(-1,-1), colors.HexColor("#DBEAFE")),
            ("FONTNAME",  (0,-1),(-1,-1), "Helvetica-Bold"),
            ("ALIGN",     (3,0), (-1,-1), "RIGHT"),
        ]))
        story.append(tabla_items)
        story.append(Spacer(1, 14))

        story.append(Paragraph(
            "El(La) suscrito(a) declara recibir a satisfaccion los materiales relacionados "
            "en la presente acta, en perfecto estado y conforme a las especificaciones tecnicas "
            "de la orden de compra de referencia.", est_body))
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=0.5, color=C_GRIS))
        story.append(Spacer(1, 10))

        rep   = cfg.get("representante_legal","Representante Legal")
        cargo = cfg.get("cargo_representante","Presidente")
        firmas_data = [[
            Paragraph(f"_____________________________<br/><b>{rep}</b><br/>{cargo}<br/>Quien entrega", est_firma),
            Paragraph("_____________________________<br/><b>__________________________</b><br/>C.C.<br/>Quien recibe", est_firma),
        ]]
        t_firmas = Table(firmas_data, colWidths=[(W-MARGEN_IZQ-MARGEN_DER)/2]*2)
        t_firmas.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER")]))
        story.append(t_firmas)

        os.makedirs(Config.PDF_FOLDER, exist_ok=True)
        pdf_path = os.path.join(Config.PDF_FOLDER, f"ACTA_{oc['codigo_completo'].replace('/','_')}.pdf")
        buf = BytesIO()
        doc_pdf = SimpleDocTemplate(buf, pagesize=A4,
            leftMargin=MARGEN_IZQ, rightMargin=MARGEN_DER,
            topMargin=MARGEN_SUP,  bottomMargin=MARGEN_INF+1*cm)
        doc_pdf.build(story, canvasmaker=NumPaginasCanvas)
        with open(pdf_path, 'wb') as f:
            f.write(buf.getvalue())
        return pdf_path

    except Exception as e:
        logger.error(f"Error acta materiales OC {orden_compra_id}: {e}")
        return None
    finally:
        conn.close()
