"""utils/validators.py — Validadores de datos para PARAGUASMJ."""
import re
from typing import Union

def validar_cedula(cedula: Union[str, int]) -> bool:
    return bool(re.match(r"^\d{7,10}$", str(cedula).strip()))

def validar_nit(nit: Union[str, int]) -> bool:
    return bool(re.match(r"^\d{8,12}(?:-\d{1})?$", str(nit).strip()))

def validar_telefono(tel: Union[str, int]) -> bool:
    return bool(re.match(r"^\+?\d{7,13}$", str(tel).strip().replace(" ", "")))

def validar_correo(correo: str) -> bool:
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", str(correo).strip()))

def validar_coordenada_lat(lat) -> bool:
    try: return -90 <= float(lat) <= 90
    except: return False

def validar_coordenada_lon(lon) -> bool:
    try: return -180 <= float(lon) <= 180
    except: return False

def sanitizar_texto(texto: str, maxlen: int = 500) -> str:
    if not texto: return ""
    import re as _re
    return _re.sub(r"\s+", " ", str(texto).strip())[:maxlen]

def sanitizar_flotante(valor, default: float = 0.0) -> float:
    try: return float(valor)
    except: return default

def es_fecha_valida(fecha_str: str, formato: str = "%Y-%m-%d") -> bool:
    from datetime import datetime
    try: datetime.strptime(fecha_str, formato); return True
    except: return False
