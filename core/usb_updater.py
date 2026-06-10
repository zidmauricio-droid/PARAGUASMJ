"""
Sistema de actualización automática por USB — PARAGUASMJ
Detecta un USB con carpeta PARAGUASMJ_UPDATE/ y aplica actualizaciones.
"""
import os
import shutil
import zipfile
import threading
import time
import logging
from pathlib import Path

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

    def _apply_zip_update(self, zip_path: Path):
        """Extrae y aplica actualización desde ZIP con protección Zip Slip."""
        try:
            app_dir_resolved = self.app_dir.resolve()
            with zipfile.ZipFile(zip_path, 'r') as zf:
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
