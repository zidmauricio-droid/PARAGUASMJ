"""
utils/validadores.py — Validación de nombres de carpetas y rutas (cross-platform)
"""
import os, re, unicodedata
from typing import Tuple

# Nombres reservados en Windows
_RESERVADOS_WINDOWS = {
    'CON','PRN','AUX','NUL',
    'COM1','COM2','COM3','COM4','COM5','COM6','COM7','COM8','COM9',
    'LPT1','LPT2','LPT3','LPT4','LPT5','LPT6','LPT7','LPT8','LPT9'
}

# Caracteres inválidos en Windows (también inválidos en Unix excepto /)
_INVALIDOS_WIN = r'[<>:"/\\|?*\x00-\x1f]'

MAX_PATH_WIN = 260
MAX_NOMBRE   = 200


def tiene_caracteres_invalidos(nombre: str) -> bool:
    return bool(re.search(_INVALIDOS_WIN, nombre))


def es_nombre_reservado_windows(nombre: str) -> bool:
    base = os.path.splitext(nombre)[0].upper()
    return base in _RESERVADOS_WINDOWS


def validar_nombre_carpeta(nombre: str) -> Tuple[bool, str]:
    if not nombre or not nombre.strip():
        return False, "El nombre no puede estar vacío"
    nombre = nombre.strip()
    if len(nombre) > MAX_NOMBRE:
        return False, f"Nombre demasiado largo (máximo {MAX_NOMBRE} caracteres)"
    if tiene_caracteres_invalidos(nombre):
        return False, "El nombre contiene caracteres inválidos (<>:\"/\\|?*)"
    if es_nombre_reservado_windows(nombre):
        return False, f"'{nombre}' es un nombre reservado del sistema"
    if nombre.startswith('.') or nombre.endswith('.') or nombre.endswith(' '):
        return False, "El nombre no puede empezar/terminar con punto o espacio"
    return True, ""


def validar_longitud_ruta(ruta: str) -> Tuple[bool, str]:
    if os.name == 'nt' and len(ruta) > MAX_PATH_WIN:
        return False, f"La ruta supera {MAX_PATH_WIN} caracteres (límite Windows)"
    return True, ""


def limpiar_nombre_carpeta(nombre: str) -> str:
    nombre = unicodedata.normalize('NFKC', nombre)
    nombre = re.sub(_INVALIDOS_WIN, '_', nombre)
    nombre = nombre.strip('. ')
    if es_nombre_reservado_windows(nombre):
        nombre = nombre + '_dir'
    return nombre or 'carpeta'


def verificar_espacio_disco(ruta: str, minimo_mb: int = 10) -> Tuple[bool, str]:
    try:
        stats = os.statvfs(ruta) if hasattr(os, 'statvfs') else None
        if stats:
            libre_mb = (stats.f_bavail * stats.f_frsize) / (1024 * 1024)
            if libre_mb < minimo_mb:
                return False, f"Espacio insuficiente: {libre_mb:.1f} MB libres (mínimo {minimo_mb} MB)"
        return True, ""
    except Exception:
        return True, ""


def get_creation_time(ruta: str) -> float:
    try:
        stat = os.stat(ruta)
        if hasattr(stat, 'st_birthtime'):   # macOS
            return stat.st_birthtime
        if os.name == 'nt':                  # Windows
            return stat.st_ctime
        return stat.st_mtime                 # Linux fallback
    except Exception:
        return 0.0
