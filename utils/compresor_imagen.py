"""
utils/compresor_imagen.py — Compresión y redimensionado seguro de imágenes al upload.
"""
from __future__ import annotations
import io, os
from datetime import datetime
from typing import Union

_MAX_DIM    = 1920          # px — cubre pantallas HD sin recorte excesivo
_QUALITY    = 85
_MAX_KB     = 300
_FORMATOS_PERMITIDOS = {"JPEG", "PNG", "WEBP", "GIF"}
_EXTS_PERMITIDAS     = {"jpg", "jpeg", "png", "gif", "webp"}


def comprimir_imagen(
    archivo: Union[bytes, io.IOBase],
    max_dim: int = _MAX_DIM,
    quality: int = _QUALITY,
) -> bytes:
    """
    Redimensiona (máx max_dim px) y comprime con calidad adaptativa.
    Devuelve bytes. Lanza ImportError si Pillow no está instalado.
    """
    try:
        from PIL import Image
    except ImportError as exc:
        raise ImportError("Pillow no instalado: pip install Pillow>=10.0.0") from exc

    img = Image.open(archivo)
    fmt = (img.format or "JPEG").upper()
    if fmt not in _FORMATOS_PERMITIDOS:
        fmt = "JPEG"

    if img.width > max_dim or img.height > max_dim:
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    if fmt == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    max_bytes = _MAX_KB * 1024
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
    """Genera nombre único y seguro para Windows (sin espacios ni colons)."""
    from werkzeug.utils import secure_filename
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = secure_filename(nombre_original) or "imagen"
    return f"editor_{ts}_{base}"


def guardar_imagen_comprimida(
    archivo,
    destino_dir: str,
    prefix: str = "img",
    max_kb: int = _MAX_KB,
) -> tuple[str, str]:
    """
    Comprime y guarda la imagen en destino_dir.
    Retorna (ruta_absoluta, nombre_archivo).
    destino_dir debe ser una ruta absoluta para compatibilidad con PyInstaller.
    """
    ext = ""
    if hasattr(archivo, "filename") and "." in archivo.filename:
        ext = archivo.filename.rsplit(".", 1)[-1].lower()
    if ext not in _EXTS_PERMITIDAS:
        ext = "jpg"

    ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = f"{prefix}_{ts}.{ext}"

    datos = comprimir_imagen(archivo, quality=min(85, max_kb))
    os.makedirs(destino_dir, exist_ok=True)
    ruta = os.path.join(destino_dir, nombre)
    with open(ruta, "wb") as f:
        f.write(datos)
    return ruta, nombre
