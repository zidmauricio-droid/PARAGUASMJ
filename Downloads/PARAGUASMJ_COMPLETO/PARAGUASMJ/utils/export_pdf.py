"""
utils/export_pdf.py — Generacion de PDF institucional con ReportLab.
Compatible con Windows sin dependencias de GTK (evita WeasyPrint en Windows).
"""
import os, logging
from datetime import datetime
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from core.database_manager import get_db
import re

logger = logging.getLogger("asuacap.pdf")

VERDE_ASUACAP = colors.HexColor("#0F6E56")
AZUL_ASUACAP  = colors.HexColor("#1E3A8A")
GRIS          = colors.HexColor("#6B7280")


def _html_a_texto(html: str) -> str:
    """Convierte HTML basico a texto plano para PDF."""
    texto = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    texto = re.sub(r"</p>", "\n\n", texto, flags=re.IGNORECASE)
    texto = re.sub(r"<[^<]+?>", "", texto)
    texto = texto.replace("&nbsp;","  ").replace("&amp;","&").replace("&lt;","<").replace("&gt;",">")
    return texto.strip()


def generar_pdf_documento(registro_id: int) -> str | None:
    """Genera PDF de un documento y retorna la ruta del archivo."""
    conn = get_db()
    try:
        doc = conn.execute("""
            SELECT r.*, c.razon_social as contacto_nombre
            FROM registro_central r
            LEFT JOIN contactos c ON r.fk_contacto_id=c.pk_contacto_id
            WHERE r.pk_registro_id=?
        """,(registro_id,)).fetchone()
        if not doc:
            return None

        contenido_row = conn.execute(
            "SELECT contenido_html FROM contenido_documento WHERE fk_registro_id=?",(registro_id,)
        ).fetchone()

        cfg = {}
        for row in conn.execute("SELECT clave,valor FROM configuracion WHERE categoria=\'Institucional\'").fetchall():
            cfg[row["clave"]] = row["valor"]

        firmantes_aprobados = conn.execute("""
            SELECT f.nombre_completo, f.cargo, o.fecha_aprobacion
            FROM autorizaciones_otp o
            JOIN firmantes f ON o.fk_firmante_id=f.pk_firmante_id
            WHERE o.fk_registro_id=? AND o.estado=\'Aprobado\'
            ORDER BY o.fecha_aprobacion
        """,(registro_id,)).fetchall()

        os.makedirs(Config.PDF_FOLDER, exist_ok=True)
        pdf_path = os.path.join(Config.PDF_FOLDER, f"{doc['codigo_completo'].replace('/','_')}.pdf")

        documento = SimpleDocTemplate(pdf_path, pagesize=LETTER,
            leftMargin=2.5*cm, rightMargin=2.5*cm,
            topMargin=2*cm, bottomMargin=2.5*cm)

        estilos = getSampleStyleSheet()
        est_titulo  = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=11,
                                      textColor=AZUL_ASUACAP, alignment=TA_CENTER, spaceAfter=4)
        est_subtit  = ParagraphStyle("subtit",  fontName="Helvetica", fontSize=9,
                                      textColor=GRIS, alignment=TA_CENTER, spaceAfter=2)
        est_normal  = ParagraphStyle("normal",  fontName="Helvetica", fontSize=10,
                                      leading=14, spaceBefore=4, spaceAfter=4)
        est_campo   = ParagraphStyle("campo",   fontName="Helvetica-Bold", fontSize=10,
                                      textColor=VERDE_ASUACAP)
        est_firma   = ParagraphStyle("firma",   fontName="Helvetica", fontSize=9,
                                      alignment=TA_CENTER)
        est_pie     = ParagraphStyle("pie",     fontName="Helvetica", fontSize=8,
                                      textColor=GRIS, alignment=TA_CENTER)

        story = []

        # Encabezado institucional
        nombre_asoc = cfg.get("nombre_completo","ASUACAP").upper()
        story.append(Paragraph(nombre_asoc, est_titulo))
        story.append(Paragraph(
            f"NIT: {cfg.get('nit','832.001.389-2')} · {cfg.get('municipio','Villeta, Cundinamarca')}",
            est_subtit))
        story.append(HRFlowable(width="100%", thickness=2, color=VERDE_ASUACAP, spaceAfter=12))

        # Datos del documento
        datos = [
            [Paragraph("Codigo:", est_campo), Paragraph(doc["codigo_completo"], est_normal)],
            [Paragraph("Fecha:", est_campo),  Paragraph(doc["fecha_radicacion"], est_normal)],
            [Paragraph("Asunto:", est_campo),  Paragraph(doc["asunto_resumen"], est_normal)],
        ]
        if doc["contacto_nombre"]:
            datos.append([Paragraph("Destinatario:", est_campo),
                           Paragraph(doc["contacto_nombre"], est_normal)])

        t_datos = Table(datos, colWidths=[4*cm, 13*cm])
        t_datos.setStyle(TableStyle([("VALIGN",(-1,-1),(0,0),"TOP"),
                                      ("GRID",(0,0),(-1,-1),0.5,colors.lightgrey)]))
        story.append(t_datos)
        story.append(Spacer(1, 0.5*cm))

        # Contenido
        if contenido_row and contenido_row["contenido_html"]:
            texto = _html_a_texto(contenido_row["contenido_html"])
            for parrafo in texto.split("\n\n"):
                if parrafo.strip():
                    story.append(Paragraph(parrafo.strip(), est_normal))
        else:
            story.append(Paragraph("[Sin contenido redactado]", est_normal))

        # Firmas
        story.append(Spacer(1, 1.5*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS))
        story.append(Spacer(1, 0.3*cm))

        if firmantes_aprobados:
            firmas_data = [[
                Paragraph(f"_________________________<br/><b>{f['nombre_completo']}</b><br/>{f['cargo']}", est_firma)
                for f in firmantes_aprobados
            ]]
        else:
            rep = cfg.get("representante_legal","Jose H. Ramirez")
            cargo = cfg.get("cargo_representante","Presidente")
            firmas_data = [[Paragraph(f"_________________________<br/><b>{rep}</b><br/>{cargo}", est_firma)]]

        t_firmas = Table(firmas_data)
        t_firmas.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"),
                                       ("VALIGN",(0,0),(-1,-1),"TOP")]))
        story.append(t_firmas)

        # Pie de pagina
        story.append(Spacer(1, 1*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS))
        story.append(Paragraph(
            f"Sistema Integrado de Gestion Documental PARAGUASMJ · "
            f"Documento generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            est_pie))

        documento.build(story)

        # Actualizar ruta en BD
        conn2 = get_db()
        conn2.execute("UPDATE registro_central SET ruta_archivo_pdf=? WHERE pk_registro_id=?",
                      (pdf_path, registro_id))
        conn2.commit(); conn2.close()

        logger.info(f"PDF generado: {pdf_path}")
        return pdf_path

    except Exception as e:
        logger.error(f"Error generando PDF para doc {registro_id}: {e}")
        return None
    finally:
        conn.close()
