"""
core/reportes_sspd.py
Generacion de reportes oficiales para SSPD (FC01, FC03, FC15),
CAR (PUEAA, Balance Hidrico) y hoja IUS.
Fuente: PROGRAMA_1.doc - estructura exacta de entregables.
"""
import sqlite3, os, logging
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from core.database_manager import get_db
from core.indicadores_ius import calcular_ius_anual

logger = logging.getLogger("sigca.sspd")

# Estilos corporativos
AZUL   = "1E3A8A"
VERDE  = "0F6E56"
GRIS   = "64748B"
BLANCO = "FFFFFF"

def _estilo_header(ws, fila, cols, color=AZUL):
    fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
    font = Font(name="Calibri", size=11, bold=True, color=BLANCO)
    alin = Alignment(horizontal="center", vertical="center", wrap_text=True)
    bord = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"),  bottom=Side(style="thin")
    )
    for c in range(1, cols+1):
        cell = ws.cell(row=fila, column=c)
        cell.fill = fill; cell.font = font
        cell.alignment = alin; cell.border = bord

def _autoajuste(ws):
    for col in ws.columns:
        mx = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(mx + 3, 55)


class ReportesSSPD:
    """Genera todos los reportes normativos en un archivo Excel."""

    def __init__(self):
        self.db_path = Config.DB_PATH
        try:
            _conn = sqlite3.connect(self.db_path)
            _rows = _conn.execute("SELECT clave,valor FROM configuracion WHERE clave IN ('nombre_completo','nombre_asociacion')").fetchall()
            _conn.close()
            self._cfg = {r[0]: r[1] for r in _rows}
        except Exception:
            self._cfg = {}

    def generar_fc15_ius(self, anio: int) -> Workbook:
        """
        Hoja FC15 para el XBRL Express de la SSPD.
        Formato exacto requerido: una hoja con variables del IUS.
        """
        ius = calcular_ius_anual(anio)
        ind = ius["indicadores"]

        wb = Workbook()
        ws = wb.active
        ws.title = "FC15 IUS"

        # Titulo
        ws["A1"] = "FC15 — ÍNDICE DE USO SOSTENIBLE (IUS)"
        ws["A1"].font = Font(name="Calibri", size=14, bold=True, color=AZUL)
        ws["A2"] = f"{self._cfg.get('nombre_asociacion','SIGCA')} — NIT 832.001.389-2 — Año {anio}"
        ws["A2"].font = Font(name="Calibri", size=10, italic=True, color=GRIS)
        ws["A3"] = f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ws["A3"].font = Font(name="Calibri", size=9, color=GRIS)

        # Cabecera tabla
        ws.append([])
        cabeceras = ["Variable", "Descripción", "Valor", "Unidad", "Referencia Normativa"]
        ws.append(cabeceras)
        _estilo_header(ws, ws.max_row, len(cabeceras))

        # Filas de datos
        filas = [
            ("IANC",        "Índice de Agua No Contabilizada",       ind.get("IANC"),         "%",      "CRA Res 688/2014"),
            ("IRAC",        "Índice de Riesgo por Acceso al Agua",   (ind.get("IRAC") or 0)*100, "%", "CRA Res 906/2019"),
            ("Continuidad", "Horas de servicio / 24",                (ind.get("continuidad") or 0)*100, "%", "CRA Res 906/2019"),
            ("Cobertura",   "Suscriptores / Total viviendas",        (ind.get("cobertura") or 0)*100,   "%", "CRA Res 906/2019"),
            ("IMA",         "Índice de Macromedición",               ind.get("IMA"),           "%",      "CRA Res 906/2019"),
            ("EET",         "Eficiencia Energética",                 ind.get("EET"),           "kWh/m³","CRA Res 906/2019"),
            ("POACg",       "Productividad Operativa",               ind.get("POACg"),         "emp/1000 susc", "CRA Res 906/2019"),
            ("IRCA",        "Índice de Riesgo Calidad del Agua",     ind.get("IRCA"),          "%",      "Decreto 1575/2007"),
            ("IUS",         "Índice de Uso Sostenible COMPUESTO",    ind.get("IUS"),           "puntos 0-100", "CRA Res 906/2019"),
            ("",            "","","",""),
            ("Producción",  "Volumen producido anual",               ind.get("produccion_m3_anual"), "m³", "PUEAA"),
            ("Facturado",   "Volumen facturado anual",               ind.get("facturado_m3_anual"),  "m³", "PUEAA"),
            ("Pérdidas",    "Agua no contabilizada anual",           ind.get("perdidas_m3_anual"),   "m³", "PUEAA"),
            ("Fallas",      "Fallas en red registradas",             ind.get("fallas_anio"),         "N°", "CAR"),
            ("Fallas/km",   "Fallas por km de red",                  ind.get("fallas_por_km"),       "fallas/km", "CAR"),
            ("Suscriptores","Total suscriptores activos",            ind.get("total_suscriptores"),  "N°", "SSPD"),
            ("Micromedidor","Suscriptores con micromedidor",         ind.get("con_micromedidor"),    "N°", "SSPD"),
        ]

        fill_alt = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        bord     = Border(left=Side(style="thin", color="DDDDDD"),
                          right=Side(style="thin", color="DDDDDD"),
                          top=Side(style="thin", color="DDDDDD"),
                          bottom=Side(style="thin", color="DDDDDD"))

        for i, row in enumerate(filas):
            ws.append(list(row))
            fila_idx = ws.max_row
            for c in range(1, 6):
                cell = ws.cell(row=fila_idx, column=c)
                cell.border = bord
                if i % 2 == 0 and row[0]:
                    cell.fill = fill_alt
                if c == 1 and row[0]:
                    cell.font = Font(bold=True, name="Calibri", size=10)
                elif c == 3:
                    cell.alignment = Alignment(horizontal="right")
                    if row[3] in ("%",) and row[2] is not None:
                        cell.number_format = "0.00"
                    elif row[2] is not None:
                        cell.number_format = "#,##0.00"

        # Resaltado IUS compuesto
        for row in ws.iter_rows(min_row=5, max_row=ws.max_row):
            if row[0].value == "IUS":
                for cell in row:
                    cell.fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
                    cell.font = Font(bold=True, name="Calibri", size=11, color=AZUL)

        _autoajuste(ws)
        return wb

    def generar_hoja_ius_excel(self, anio: int) -> Workbook:
        """
        Hoja IUS completa estilo INFORMACION IUS 2024.xlsx.
        12 hojas mensuales + resumen anual.
        """
        conn = get_db()
        wb = Workbook()
        wb.remove(wb.active)

        meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                 "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

        datos_anuales = []
        for mes in range(1, 13):
            bh = conn.execute("""
                SELECT COALESCE(produccion_m3,0) as p,
                       COALESCE(facturado_m3,0)  as f
                FROM balance_hidrico WHERE anio=? AND mes=?
            """, (anio, mes)).fetchone()
            prod = float(bh["p"]) if bh else 0
            fac  = float(bh["f"]) if bh else 0
            ianc_val = round((prod - fac)/prod*100, 2) if prod > 0 else None
            datos_anuales.append({
                "mes": meses[mes-1], "produccion": prod,
                "facturado": fac, "perdidas": prod - fac,
                "ianc": ianc_val
            })

        # Hoja resumen anual
        ws = wb.create_sheet("Resumen Anual IUS")
        ws["A1"] = f"{self._cfg.get('nombre_asociacion','SIGCA')} — HOJA IUS {anio}"
        ws["A1"].font = Font(name="Calibri", size=14, bold=True, color=AZUL)

        ws.append([])
        hdrs = ["Mes","Produccion m3","Facturado m3","Perdidas m3","IANC %"]
        ws.append(hdrs)
        _estilo_header(ws, ws.max_row, len(hdrs))

        for d in datos_anuales:
            ws.append([d["mes"], d["produccion"], d["facturado"],
                       d["perdidas"], d["ianc"]])

        # Totales
        n = len(datos_anuales) + 4
        ws.append(["TOTAL ANUAL",
                   f"=SUM(B5:B{n})", f"=SUM(C5:C{n})",
                   f"=SUM(D5:D{n})",
                   f"=IF(B{n+1}>0,(B{n+1}-C{n+1})/B{n+1}*100,0)"])
        row_tot = ws.max_row
        for c in range(1, 6):
            cell = ws.cell(row=row_tot, column=c)
            cell.font = Font(bold=True, name="Calibri")
            cell.fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")

        _autoajuste(ws)

        # Hoja indicadores completos
        ius_data = calcular_ius_anual(anio)
        ws2 = wb.create_sheet("Indicadores IUS")
        ws2["A1"] = f"INDICADORES IUS COMPLETOS — {anio}"
        ws2["A1"].font = Font(name="Calibri", size=13, bold=True, color=AZUL)
        ws2.append([])
        ws2.append(["Indicador", "Valor", "Unidad"])
        _estilo_header(ws2, ws2.max_row, 3)
        for k, v in ius_data["indicadores"].items():
            ws2.append([k, v, ""])
        _autoajuste(ws2)

        conn.close()
        return wb

    def generar_balance_hidrico_car(self, anio: int, trimestre: int) -> Workbook:
        """Balance hidrico trimestral para reporte CAR/PUEAA."""
        meses_map = {1:("01","02","03"), 2:("04","05","06"),
                     3:("07","08","09"), 4:("10","11","12")}
        meses = meses_map.get(trimestre, ("01","02","03"))
        conn = sqlite3.connect(Config.DB_PATH)

        wb = Workbook()
        ws = wb.active
        ws.title = f"Balance T{trimestre} {anio}"

        ws["A1"] = f"{self._cfg.get('nombre_asociacion','SIGCA')} — BALANCE HÍDRICO MENSUAL — REPORTE CAR/PUEAA"
        ws["A1"].font = Font(name="Calibri", size=13, bold=True, color=AZUL)
        ws["A2"] = f"Trimestre {trimestre} — Año {anio} | NIT 832.001.389-2 | Villeta, Cundinamarca"
        ws["A2"].font = Font(name="Calibri", size=10, italic=True, color=GRIS)
        ws.append([])

        hdrs = ["Mes","Vol.Producido m³","Vol.Facturado m³","Pérdidas m³","IANC %","Observaciones"]
        ws.append(hdrs)
        _estilo_header(ws, ws.max_row, len(hdrs))

        for m in meses:
            bh = conn.execute(
                "SELECT * FROM balance_hidrico WHERE anio=? AND mes=?",
                (anio, int(m))
            ).fetchone()
            if bh:
                prod = float(bh[3]); fac = float(bh[4])
                perd = round(prod - fac, 2)
                ianc_val = round((prod-fac)/prod*100, 2) if prod > 0 else 0
                ws.append([f"{anio}-{m}", prod, fac, perd, ianc_val, bh[6] or ""])
            else:
                ws.append([f"{anio}-{m}", 0, 0, 0, 0, "Sin datos"])

        _autoajuste(ws)
        conn.close()
        return wb
