"""
utils/compresor_imagen.py — Compresión y redimensionado seguro de imágenes al upload.
"""
from __future__ import annotations
import io
from datetime import datetime
from typing import Union

_MAX_WIDTH  = 1200
_MAX_HEIGHT = 1200
_QUALITY    = 85
_FORMATOS_PERMITIDOS = {"JPEG", "PNG", "WEBP", "GIF"}


def comprimir_imagen(
    archivo: Union[bytes, io.IOBase],
    max_width: int = _MAX_WIDTH,
    max_height: int = _MAX_HEIGHT,
    quality: int = _QUALITY,
) -> bytes:
    """
    Redimensiona y comprime una imagen. Devuelve bytes comprimidos.
    Lanza ImportError si Pillow no está instalado.
    Lanza ValueError si el formato no está permitido.
    """
    try:
        from PIL import Image
    except ImportError as exc:
        raise ImportError("Pillow no instalado: pip install Pillow>=10.0.0") from exc

    img = Image.open(archivo)
    fmt = (img.format or "JPEG").upper()
    if fmt not in _FORMATOS_PERMITIDOS:
        fmt = "JPEG"

    if img.width > max_width or img.height > max_height:
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    # Convertir RGBA→RGB para JPEG (no admite canal alfa)
    if fmt == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Reducción adaptativa de calidad hasta alcanzar max_kb
    max_bytes = 300 * 1024
    buf = io.BytesIO()
    q = quality
    while q >= 20:
        buf.seek(0); buf.truncate()
        img.save(buf, format=fmt, quality=q, optimize=True)
        if buf.tell() <= max_bytes:
            break
        q -= 10
    return buf.getvalue()


def nombre_upload_seguro(nombre_original: str) -> str:
    """Genera nombre de archivo único y seguro para Windows (sin espacios ni colons)."""
    from werkzeug.utils import secure_filename
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = secure_filename(nombre_original) or "imagen"
    return f"editor_{ts}_{base}"
