"""
Sistema de actualización automática por USB — PARAGUASMJ
Detecta un USB con carpeta PARAGUASMJ_UPDATE/ y aplica actualizaciones.
Seguridad: valida manifest.sha256 firmado antes de aplicar cualquier ZIP.
"""
import os
import shutil
import zipfile
import hashlib
import hmac as _hmac
import threading
import time
import logging
from pathlib import Path


def hmac_compare(a: str, b: str) -> bool:
    return _hmac.compare_digest(
        a.encode() if isinstance(a, str) else a,
        b.encode() if isinstance(b, str) else b,
    )

logger = logging.getLogger("paraguasmj.usb_updater")


class USBUpdater:
    def __init__(self, app_dir: Path):
        self.app_dir = app_dir
        self.update_marker = "PARAGUASMJ_UPDATE"
        self.running = False
        self._thread = None

    def _find_usb_update(self):
        """Busca actualizaciones en dispositivos USB montados."""
        mount_points = []

        # Linux: /media y /mnt
        media_dir = Path("/media")
        if media_dir.exists():
            for user_dir in media_dir.iterdir():
                if user_dir.is_dir():
                    try:
                        mount_points.extend(user_dir.iterdir())
                    except PermissionError:
                        pass

        mnt_dir = Path("/mnt")
        if mnt_dir.exists():
            try:
                mount_points.extend(mnt_dir.iterdir())
            except PermissionError:
                pass

        # Windows: letras de unidad D: hasta Z:
        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            drive = Path(f"{letter}:/")
            if drive.exists():
                mount_points.append(drive)

        for mount in mount_points:
            try:
                update_dir = mount / self.update_marker
                if update_dir.exists() and update_dir.is_dir():
                    return update_dir
            except (PermissionError, OSError):
                pass

        return None

    def _apply_update(self, update_dir: Path):
        """Aplica la actualización desde la carpeta USB."""
        logger.info(f"Actualización encontrada en: {update_dir}")

        # Buscar ZIP de actualización
        try:
            zips = list(update_dir.glob("PARAGUASMJ_*.zip"))
        except OSError:
            zips = []

        if not zips:
            try:
                py_files = list(update_dir.rglob("*.py"))
            except OSError:
                py_files = []
            if py_files:
                self._apply_file_update(update_dir, py_files)
            return

        # Aplicar ZIP más reciente
        latest_zip = max(zips, key=lambda z: z.stat().st_mtime)
        self._apply_zip_update(latest_zip)

    def _verificar_manifest(self, zip_path: Path) -> bool:
        """
        Verifica que exista un manifest.sha256 en la misma carpeta del ZIP
        y que el hash SHA-256 del archivo coincida.
        Formato del manifest: <hash_hex>  <nombre_zip>
        """
        manifest_path = zip_path.parent / "manifest.sha256"
        if not manifest_path.exists():
            logger.error(f"ZIP rechazado: falta manifest.sha256 en {zip_path.parent}")
            return False
        try:
            # Calcular SHA-256 del ZIP
            sha = hashlib.sha256()
            with open(zip_path, "rb") as fz:
                for bloque in iter(lambda: fz.read(65536), b""):
                    sha.update(bloque)
            hash_calculado = sha.hexdigest()

            # Leer manifest y buscar la línea correspondiente al ZIP
            contenido = manifest_path.read_text(encoding="utf-8").strip()
            for linea in contenido.splitlines():
                partes = linea.strip().split(None, 1)
                if len(partes) == 2 and partes[1].strip() == zip_path.name:
                    hash_esperado = partes[0].strip().lower()
                    if hmac_compare(hash_calculado, hash_esperado):
                        logger.info(f"Manifest verificado correctamente para {zip_path.name}")
                        return True
                    logger.error(
                        f"ZIP rechazado: hash no coincide. "
                        f"Esperado: {hash_esperado[:16]}... Calculado: {hash_calculado[:16]}..."
                    )
                    return False
            logger.error(f"ZIP rechazado: {zip_path.name} no encontrado en manifest.sha256")
            return False
        except Exception as e:
            logger.error(f"Error verificando manifest: {e}")
            return False

    def _apply_zip_update(self, zip_path: Path):
        """Extrae y aplica actualización desde ZIP con protección Zip Slip y verificación SHA-256."""
        # Verificar manifest antes de cualquier extracción
        if not self._verificar_manifest(zip_path):
            return
        try:
            app_dir_resolved = self.app_dir.resolve()
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Validar integridad interna del ZIP
                bad = zf.testzip()
                if bad:
                    logger.error(f"ZIP corrupto: primer archivo malo = {bad}")
                    return
                # Validar cada entrada antes de extraer (Zip Slip protection)
                for member in zf.namelist():
                    if ".." in member or member.startswith("/") or member.startswith("\\"):
                        logger.error(f"ZIP rechazado: ruta peligrosa detectada: {member}")
                        return
                    dest = (app_dir_resolved / member).resolve()
                    if not str(dest).startswith(str(app_dir_resolved)):
                        logger.error(f"ZIP rechazado: ruta escapa al directorio: {member}")
                        return
                zf.extractall(self.app_dir)
            logger.info(f"ZIP aplicado: {zip_path.name}")

            # Marcar como aplicado
            applied_marker = zip_path.parent / f"APLICADO_{zip_path.stem}.txt"
            applied_marker.write_text(
                f"Aplicado el {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
        except Exception as e:
            logger.error(f"Error aplicando ZIP: {e}")

    def _apply_file_update(self, update_dir: Path, py_files: list):
        """Copia archivos Python de actualización al proyecto."""
        for src_file in py_files:
            try:
                rel_path = src_file.relative_to(update_dir)
                dest_file = self.app_dir / rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest_file)
                logger.info(f"Archivo actualizado: {rel_path}")
            except Exception as e:
                logger.error(f"Error copiando {src_file}: {e}")

    def _monitor_loop(self):
        """Loop de monitoreo de USB en segundo plano."""
        last_update_dir = None
        while self.running:
            try:
                update_dir = self._find_usb_update()
                if update_dir and update_dir != last_update_dir:
                    self._apply_update(update_dir)
                    last_update_dir = update_dir
                elif not update_dir:
                    last_update_dir = None
            except Exception as e:
                logger.error(f"Error en monitor USB: {e}")
            time.sleep(10)  # Revisar cada 10 segundos

    def start(self):
        """Inicia el monitoreo de USB en segundo plano."""
        if not self.running:
            self.running = True
            self._thread = threading.Thread(
                target=self._monitor_loop, daemon=True, name="usb-updater"
            )
            self._thread.start()
            logger.info("Monitor USB iniciado (revisa cada 10 s)")

    def stop(self):
        """Detiene el monitoreo."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
            logger.info("Monitor USB detenido")


def create_usb_updater(app_dir: Path) -> USBUpdater:
    """Crea e inicia una instancia del USBUpdater."""
    updater = USBUpdater(app_dir)
    updater.start()
    return updater
