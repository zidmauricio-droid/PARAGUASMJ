"""utils/helpers.py — Funciones auxiliares para PARAGUASMJ."""
from datetime import datetime, date, timedelta
from typing import Union, Optional

def formatear_moneda(valor) -> str:
    if valor is None: return "COP $0,00"
    try:
        v = float(valor); neg = v < 0; v = abs(v)
        ent = int(v); dec = round((v - ent) * 100)
        return "COP $" + ("-" if neg else "") + f"{ent:,}".replace(",",".") + f",{dec:02d}"
    except: return "COP $0,00"

def calcular_ianc(produccion, facturado) -> Optional[float]:
    try:
        p, f = float(produccion or 0), float(facturado or 0)
        return round((p - f) / p * 100, 2) if p > 0 else None
    except: return None

def truncar(texto, maxlen: int = 60) -> str:
    if not texto: return ""
    t = str(texto).strip()
    return t if len(t) <= maxlen else t[:maxlen] + "..."

def fecha_actual_formato(fmt: str = "%Y-%m-%d") -> str:
    return datetime.now().strftime(fmt)

def diferencia_dias(fecha_inicio: date, fecha_fin: date) -> int:
    if not isinstance(fecha_inicio, date) or not isinstance(fecha_fin, date): return 0
    return (fecha_fin - fecha_inicio).days
