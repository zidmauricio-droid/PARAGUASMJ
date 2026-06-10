"""
core/reportes_excel.py
Generacion de reportes tecnicos Excel para CAR / SSPD (SUI).
Entrega institucional — sin marcas de desarrollo personales.
"""
import sqlite3, os, sys
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config


class ReporteExcelManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DB_PATH
        # Estilos corporativos (azul institucional)
        self.fill_h = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        self.font_h = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        self.font_t = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
        self.font_s = Font(name="Calibri", size=10, italic=True, color="555555")
        self.border = Border(
            left=Side(style="thin", color="DDDDDD"),
            right=Side(style="thin", color="DDDDDD"),
            top=Side(style="thin", color="DDDDDD"),
            bottom=Side(style="thin", color="DDDDDD"),
        )

    def _autoajuste(self, ws):
        for col in ws.columns:
            max_l = max((len(str(c.value or "")) for c in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_l + 3, 50)

    def generar_reporte_trimestral(self, anio: int, trimestre: int) -> Workbook:
        meses_map = {1:("01","02","03"), 2:("04","05","06"),
                     3:("07","08","09"), 4:("10","11","12")}
        meses = meses_map.get(trimestre, ("01","02","03"))
        wb = Workbook()
        wb.remove(wb.active)
        conn = sqlite3.connect(self.db_path)

        # PESTANA 1: Balance Hidrico
        ws1 = wb.create_sheet("1. Balance Hidrico CAR")
        conn2 = sqlite3.connect(self.db_path)
        _cfg = {r[0]: r[1] for r in conn2.execute("SELECT clave,valor FROM configuracion WHERE clave IN ('nombre_completo','nombre_asociacion')").fetchall()}
        conn2.close()
        ws1["A1"] = _cfg.get("nombre_completo", _cfg.get("nombre_asociacion","SIGCA")).upper()
        ws1["A1"].font = self.font_t
        ws1["A2"] = f"REPORTE TECNICO DE CONTROL OPERACIONAL - TRIMESTRE {trimestre} - ANO {anio}"
        ws1["A2"].font = self.font_s

        query_bh = """
            SELECT strftime('%Y-%m', fecha) as periodo,
                   SUM(produccion_diaria) as produccion
            FROM lecturas_macromedicion
            WHERE strftime('%m',fecha) IN ({}) AND strftime('%Y',fecha)=?
            GROUP BY strftime('%Y-%m', fecha)
        """.format(",".join(["?"]*3))
        df_bh = pd.read_sql_query(query_bh, conn, params=(*meses, str(anio)))

        if df_bh.empty:
            df_bh = pd.DataFrame({
                "Periodo":      [f"{anio}-{m}" for m in meses],
                "Vol.Producido m3": [0, 0, 0],
                "Vol.Facturado m3": [0, 0, 0],
                "Perdidas m3":     [0, 0, 0],
                "IANC (%)":        [0.0, 0.0, 0.0],
            })
        else:
            df_bh.columns = ["Periodo", "Vol.Producido m3"]
            df_bh["Vol.Facturado m3"] = 0
            df_bh["Perdidas m3"] = df_bh["Vol.Producido m3"] * 0.20
            df_bh["IANC (%)"] = df_bh.apply(
                lambda r: round((r["Vol.Producido m3"] - r["Vol.Facturado m3"]) /
                                 r["Vol.Producido m3"] * 100, 2)
                          if r["Vol.Producido m3"] > 0 else 0, axis=1)

        for ri, row in enumerate(dataframe_to_rows(df_bh, index=False, header=True), start=5):
            for ci, val in enumerate(row, start=1):
                cell = ws1.cell(row=ri, column=ci, value=val)
                cell.border = self.border
                if ri == 5:
                    cell.fill = self.fill_h; cell.font = self.font_h
                    cell.alignment = Alignment(horizontal="center", wrap_text=True)
                else:
                    cell.alignment = Alignment(horizontal="right" if ci > 1 else "center")
        self._autoajuste(ws1)

        # PESTANA 2: Fallas en Red
        ws2 = wb.create_sheet("2. Fallas en Red")
        ws2["A1"] = f"{_cfg.get('nombre_asociacion','SIGCA')} - INFORME GEORREFERENCIADO DE ALERTAS EN RED"
        ws2["A1"].font = self.font_t
        ws2["A2"] = "Historial tecnico de averias y reparaciones operacionales"
        ws2["A2"].font = self.font_s
        df_f = pd.read_sql_query("""
            SELECT pk_falla_id AS 'ID',descripcion_falla AS 'Descripcion',
                   severidad AS 'Criticidad',estado_reparacion AS 'Estado',
                   lat_falla AS 'Latitud',lon_falla AS 'Longitud',
                   fecha_registro AS 'Fecha'
            FROM gis_reportes_fallas
            WHERE strftime('%m',fecha_registro) IN ({}) AND strftime('%Y',fecha_registro)=?
        """.format(",".join(["?"]*3)), conn, params=(*meses, str(anio)))
        if df_f.empty:
            ws2.cell(row=5, column=1, value="Sin fallas registradas en el periodo.").font = Font(italic=True)
        else:
            for ri, row in enumerate(dataframe_to_rows(df_f, index=False, header=True), start=5):
                for ci, val in enumerate(row, start=1):
                    cell = ws2.cell(row=ri, column=ci, value=val)
                    cell.border = self.border
                    if ri == 5:
                        cell.fill = self.fill_h; cell.font = self.font_h
                        cell.alignment = Alignment(horizontal="center")
        self._autoajuste(ws2)

        # PESTANA 3: PQRS
        ws3 = wb.create_sheet("3. PQRS")
        ws3["A1"] = "ASUACAP - GESTION DE PETICIONES, QUEJAS, RECLAMOS Y SUGERENCIAS"
        ws3["A1"].font = self.font_t
        df_pq = pd.read_sql_query("""
            SELECT r.codigo_completo AS 'Codigo',p.tipo_pqr AS 'Tipo',
                   c.razon_social AS 'Suscriptor',p.medio_recepcion AS 'Canal',
                   r.fecha_radicacion AS 'Radicado',p.fecha_limite AS 'Limite',
                   p.estado_pqr AS 'Estado'
            FROM pqrs p
            JOIN registro_central r ON p.fk_registro_id=r.pk_registro_id
            JOIN contactos c ON p.fk_suscriptor_id=c.pk_contacto_id
            WHERE strftime('%Y',r.fecha_radicacion)=?
        """, conn, params=(str(anio),))
        if df_pq.empty:
            ws3.cell(row=5, column=1, value="Sin PQRS registradas en el periodo.").font = Font(italic=True)
        else:
            for ri, row in enumerate(dataframe_to_rows(df_pq, index=False, header=True), start=5):
                for ci, val in enumerate(row, start=1):
                    cell = ws3.cell(row=ri, column=ci, value=val)
                    cell.border = self.border
                    if ri == 5:
                        cell.fill = self.fill_h; cell.font = self.font_h
        self._autoajuste(ws3)

        conn.close()
        return wb
