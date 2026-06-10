"""
core/logo_manager.py — Gestor central del logo institucional SIGCA.

El logo se carga UNA SOLA VEZ en Configuración y se usa automáticamente en:
  - Membrete PDF (ReportLab)
  - Membrete Word (python-docx)  
  - Excel reportes (openpyxl)
  - Navbar del sistema web
  - Editor TipTap (membrete visible al redactar)
  - Todo documento generado por el sistema
"""
import os, base64, sqlite3
from typing import Optional

LOGO_DIR      = os.path.join("static", "uploads", "logos")
EXTS_OK       = {"png", "jpg", "jpeg", "webp"}


def guardar_logo(archivo_bytes: bytes, nombre_original: str, db_path: str) -> dict:
    """Guarda el logo en disco y BD. Retorna {ok, path, base64, error}."""
    ext = nombre_original.rsplit(".", 1)[-1].lower()
    if ext not in EXTS_OK:
        return {"ok": False, "error": f"Solo PNG, JPG o WEBP"}

    os.makedirs(LOGO_DIR, exist_ok=True)
    nombre_final = f"logo_sigca.{ext}"
    ruta         = os.path.join(LOGO_DIR, nombre_final)
    with open(ruta, "wb") as f:
        f.write(archivo_bytes)

    mime    = "image/png" if ext == "png" else f"image/{ext}"
    b64_str = base64.b64encode(archivo_bytes).decode("utf-8")
    data_url = f"data:{mime};base64,{b64_str}"

    conn = sqlite3.connect(db_path)
    for k, v in [("logo_path", ruta), ("logo_base64", data_url), ("logo_nombre", nombre_original)]:
        conn.execute("INSERT OR REPLACE INTO configuracion (clave,valor) VALUES (?,?)", (k, v))
    conn.commit(); conn.close()
    return {"ok": True, "path": ruta, "base64": data_url}


def obtener_logo(db_path: str) -> dict:
    """Retorna el logo y datos institucionales para cualquier módulo."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    filas = conn.execute("""
        SELECT clave, valor FROM configuracion
        WHERE clave IN (
            'logo_path','logo_base64','logo_nombre',
            'nombre_completo','nombre_asociacion','nit',
            'municipio','correo_oficial','representante_legal',
            'eslogan','color_primario','color_secundario',
            'telefono_oficina','secretaria','cargo_representante'
        )
    """).fetchall()
    conn.close()
    cfg = {r["clave"]: (r["valor"] or "") for r in filas}

    tiene = bool(cfg.get("logo_base64","").startswith("data:"))
    path  = cfg.get("logo_path","")
    if path and not os.path.exists(path):
        path = ""

    return {
        "tiene_logo":      tiene,
        "path":            path,
        "base64":          cfg.get("logo_base64",""),
        "nombre":          cfg.get("logo_nombre",""),
        "nombre_asoc":     cfg.get("nombre_completo", cfg.get("nombre_asociacion","SIGCA")),
        "nombre_corto":    cfg.get("nombre_asociacion","SIGCA"),
        "nit":             cfg.get("nit","832.001.389-2"),
        "municipio":       cfg.get("municipio","Villeta, Cundinamarca"),
        "correo":          cfg.get("correo_oficial",""),
        "representante":   cfg.get("representante_legal",""),
        "cargo_rep":       cfg.get("cargo_representante","Representante Legal"),
        "eslogan":         cfg.get("eslogan",""),
        "color_primario":  cfg.get("color_primario","#1E3A8A"),
        "color_secundario":cfg.get("color_secundario","#0F6E56"),
        "telefono":        cfg.get("telefono_oficina",""),
        "secretaria":      cfg.get("secretaria",""),
    }


def membrete_html(db_path: str, codigo: str = "", titulo: str = "",
                  version: str = "01", clasificacion: str = "Uso Interno",
                  aprobado_por: str = "", fecha: str = "") -> str:
    """
    Genera el membrete HTML exacto al del documento institucional compartido:
    ╔══════════════════════════════════════╦═══════╗
    ║  Nombre asociación · NIT · municipio ║  LOGO ║
    ╠══════════════════════════════════════╩═══════╣
    ║  Título                          Fecha:      ║
    ╠═══════════════════════╦══════════════════════╣
    ║  Clasificación        ║  Código              ║
    ╠═══════════════════════╬═══════╦══════════════╣
    ║  Aprobado por         ║Versión║  Página      ║
    ╚═══════════════════════╩═══════╩══════════════╝
    """
    from datetime import date as dt
    info     = obtener_logo(db_path)
    fecha_d  = fecha or str(dt.today().year)
    aprobado = aprobado_por or info["representante"]
    cp       = info["color_primario"]

    img_tag = ""
    if info["tiene_logo"]:
        img_tag = (f'<img src="{info["base64"]}" '
                   f'style="height:52px;max-width:75px;object-fit:contain;">')
    else:
        img_tag = (f'<div style="width:60px;height:52px;background:{cp};color:#fff;'
                   f'border-radius:6px;display:flex;align-items:center;justify-content:center;'
                   f'font-weight:800;font-size:10px;text-align:center;line-height:1.2;">'
                   f'{info["nombre_corto"][:6]}</div>')

    B = "border:1px solid #94a3b8;"
    P = "padding:5px 8px;"
    return f"""<table style="width:100%;border-collapse:collapse;
font-family:Calibri,Arial,sans-serif;font-size:10px;{B}">
  <tr>
    <td style="{P}border-bottom:1px solid #94a3b8;border-right:1px solid #94a3b8;" colspan="3">
      <strong style="font-size:11px;color:{cp};">{info['nombre_asoc'].upper()}</strong><br>
      <span style="color:#475569;">NIT: {info['nit']} &nbsp;·&nbsp; {info['municipio']}</span>
    </td>
    <td style="{P}border-bottom:1px solid #94a3b8;text-align:center;vertical-align:middle;width:80px;" rowspan="4">
      {img_tag}
    </td>
  </tr>
  <tr>
    <td style="{P}border-bottom:1px solid #94a3b8;border-right:1px solid #94a3b8;" colspan="3">
      <strong>Título:</strong> {titulo} &nbsp;&nbsp;&nbsp; <strong>Fecha:</strong> {fecha_d}
    </td>
  </tr>
  <tr>
    <td style="{P}border-bottom:1px solid #94a3b8;border-right:1px solid #94a3b8;" colspan="2">
      <strong>Clasificación:</strong> {clasificacion}
    </td>
    <td style="{P}border-bottom:1px solid #94a3b8;border-right:1px solid #94a3b8;">
      <strong>Código</strong> {codigo}
    </td>
  </tr>
  <tr>
    <td style="{P}border-right:1px solid #94a3b8;">
      <strong>Aprobado por:</strong> {aprobado}
    </td>
    <td style="{P}border-right:1px solid #94a3b8;">
      <strong>Versión:</strong> {version}
    </td>
    <td style="{P}border-right:1px solid #94a3b8;">
      <strong>Página:</strong> 1 de 1
    </td>
  </tr>
</table>
<div style="height:3px;background:{cp};margin:0 0 14px 0;"></div>"""


def pie_pagina_html(db_path: str) -> str:
    """Pie de página institucional."""
    info = obtener_logo(db_path)
    return f"""<div style="margin-top:24px;border-top:1px solid #cbd5e1;padding-top:6px;
font-family:Calibri,Arial,sans-serif;font-size:9px;color:#64748b;text-align:center;">
  {info['correo']} &nbsp;·&nbsp; {info.get("correo_institucional","")} &nbsp;·&nbsp; {info['telefono']}
</div>"""


def membrete_docx(doc, db_path: str, codigo: str = "", titulo: str = "",
                  version: str = "01", clasificacion: str = "Uso Interno",
                  aprobado_por: str = "", fecha: str = "") -> None:
    """
    Inserta el membrete institucional en un documento python-docx,
    replicando exactamente la tabla de la imagen compartida.
    """
    from docx.shared import Pt, RGBColor, Cm, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    import tempfile

    info    = obtener_logo(db_path)
    fecha_d = fecha or __import__('datetime').date.today().strftime("%Y")
    aprobado = aprobado_por or info["representante"]

    # Color primario como RGB
    hex_c = info["color_primario"].lstrip("#")
    rgb   = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))
    AZUL  = RGBColor(*rgb)

    # Tabla de membrete: 4 filas x 4 columnas
    tabla = doc.add_table(rows=4, cols=4)
    tabla.style = "Table Grid"

    def _set_cell(cell, texto, bold=False, color=None, size=9):
        cell.text = ""
        p   = cell.paragraphs[0]
        run = p.add_run(texto)
        run.font.size  = Pt(size)
        run.font.bold  = bold
        if color: run.font.color.rgb = color

    # Fila 0: nombre institución (colspan 3) + logo (rowspan 4)
    c00 = tabla.rows[0].cells[0]
    c00.merge(tabla.rows[0].cells[2])
    _set_cell(c00,
              f"{info['nombre_asoc'].upper()}\n"
              f"NIT: {info['nit']} · {info['municipio']}",
              bold=True, color=AZUL, size=10)

    # Celda logo (columna 3, filas 0-3 fusionadas)
    c03 = tabla.rows[0].cells[3]
    for i in range(1, 4):
        c03 = c03.merge(tabla.rows[i].cells[3])
    c03.text = ""
    if info["tiene_logo"] and info["path"]:
        try:
            p_logo = c03.paragraphs[0]
            p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_logo = p_logo.add_run()
            run_logo.add_picture(info["path"], width=Inches(0.9))
        except Exception:
            _set_cell(c03, info["nombre_corto"], bold=True)
    else:
        _set_cell(c03, info["nombre_corto"], bold=True)

    # Fila 1: Título + Fecha
    c10 = tabla.rows[1].cells[0]
    c10.merge(tabla.rows[1].cells[2])
    _set_cell(c10, f"Título: {titulo}     Fecha: {fecha_d}", size=9)

    # Fila 2: Clasificación + Código
    _set_cell(tabla.rows[2].cells[0].merge(tabla.rows[2].cells[1]),
              f"Clasificación: {clasificacion}", size=9)
    _set_cell(tabla.rows[2].cells[2], f"Código: {codigo}", size=9)

    # Fila 3: Aprobado + Versión + Página
    _set_cell(tabla.rows[3].cells[0], f"Aprobado por: {aprobado}", size=9)
    _set_cell(tabla.rows[3].cells[1], f"Versión: {version}", size=9)
    _set_cell(tabla.rows[3].cells[2], "Página: 1 de 1", size=9)

    # Línea azul separadora
    from docx.shared import Pt as DPt
    doc.add_paragraph()


def membrete_pdf(story, cfg_dict: dict, db_path: str,
                 tipo_doc: str, codigo: str, fecha_doc: str,
                 destinatario: str = "") -> None:
    """
    Inserta el membrete en un ReportLab story.
    Reemplaza la función _membrete anterior en pdf_profesional.py.
    """
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import io

    info = obtener_logo(db_path)
    W    = 21.0 * 28.35   # A4 en puntos
    ML   = 1.8  * 28.35
    MR   = 1.5  * 28.35
    col  = W - ML - MR

    cp   = colors.HexColor(info["color_primario"])
    GRIS = colors.HexColor("#475569")
    BLAN = colors.white

    sN = ParagraphStyle("sN", fontName="Helvetica-Bold",  fontSize=11,
                         textColor=cp,   alignment=TA_CENTER, leading=13)
    sD = ParagraphStyle("sD", fontName="Helvetica",       fontSize=8,
                         textColor=GRIS, alignment=TA_CENTER)

    # Celda de datos institucionales
    datos = [
        Paragraph(info["nombre_asoc"].upper(), sN),
        Spacer(1, 3),
        Paragraph(f"NIT {info['nit']}  ·  {info['municipio']}", sD),
    ]

    # Celda del logo
    if info["tiene_logo"] and info["path"]:
        try:
            logo_cell = Image(info["path"], width=60, height=50,
                              kind="proportional")
        except Exception:
            logo_cell = Paragraph(info["nombre_corto"], sN)
    elif info["tiene_logo"] and info["base64"].startswith("data:"):
        try:
            raw = info["base64"].split(",", 1)[1]
            logo_cell = Image(io.BytesIO(__import__('base64').b64decode(raw)),
                              width=60, height=50, kind="proportional")
        except Exception:
            logo_cell = Paragraph(info["nombre_corto"], sN)
    else:
        logo_cell = Paragraph(info["nombre_corto"], sN)

    t = Table([[datos, logo_cell]],
              colWidths=[col - 70, 70])
    t.setStyle(TableStyle([
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW",  (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
    ]))
    story.append(t)
    story.append(Spacer(1, 4))

    # Línea azul
    from reportlab.platypus import HRFlowable
    story.append(HRFlowable(width="100%", thickness=2.5, color=cp, spaceAfter=8))

    # Metadatos del documento
    sMeta = ParagraphStyle("sMeta", fontName="Helvetica", fontSize=9,
                            textColor=colors.black, alignment=TA_LEFT)
    sBold = ParagraphStyle("sBold", fontName="Helvetica-Bold", fontSize=9,
                            textColor=colors.black, alignment=TA_LEFT)
    meta  = [[Paragraph("Tipo:", sBold), Paragraph(tipo_doc, sMeta)],
             [Paragraph("Código:", sBold), Paragraph(codigo, sMeta)],
             [Paragraph("Fecha:", sBold), Paragraph(fecha_doc, sMeta)]]
    if destinatario:
        meta.append([Paragraph("Destinatario:", sBold),
                     Paragraph(destinatario, sMeta)])
    tm = Table(meta, colWidths=[col * 0.25, col * 0.75])
    tm.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("PADDING",     (0, 0), (-1, -1), 5),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
    ]))
    story.append(tm)
    story.append(Spacer(1, 10))
