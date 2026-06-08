"""
utils/file_manager.py — Gestor de estructura documental en 12 módulos
"""
import os, shutil, time, logging
from typing import Dict, List, Tuple, Optional, Any
from utils.validadores import validar_nombre_carpeta, validar_longitud_ruta, verificar_espacio_disco

logger = logging.getLogger("asuacap.file_manager")

_MODULOS = {
    "PQRS":           ["Recibidos", "En_Proceso", "Respondidos", "Archivados"],
    "Finanzas":       ["Presupuesto", "Facturas", "Recaudos", "Informes_Financieros"],
    "Proyectos":      ["Activos", "Completados", "Suspendidos", "Licitaciones"],
    "GIS":            ["Mapas", "Redes", "Predios", "Actualizaciones"],
    "Emergencias":    ["Reportes", "Protocolos", "Evidencias", "Seguimientos"],
    "Calidad_Agua":   ["Analisis", "Certificados", "IRCA", "Reportes_SIVICAP"],
    "Legal":          ["Contratos", "Resoluciones", "Conceptos", "Demandas"],
    "Suscriptores":   ["Solicitudes", "Contratos", "Reclamos", "Actualizaciones"],
    "Nivel_Quebrada": ["Datos_Diarios", "Reportes_Mensuales", "Alertas", "Historicos"],
    "Backups":        ["Diarios", "Semanales", "Mensuales", "Anuales"],
    "Config":         ["Sistema", "Usuarios", "Parametros", "Versiones"],
    "Comunicaciones": ["Oficios", "Actas", "Circulares", "Correspondencia"],
}


class FileManager:
    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), '..', 'uploads'
            )
        self.base_dir = os.path.abspath(base_dir)
        self._cache: Dict[str, Any] = {}
        self._cache_ts: float = 0.0
        self._cache_ttl: float = 60.0

    def _ruta_modulo(self, modulo: str) -> str:
        return os.path.join(self.base_dir, modulo)

    def crear_estructura_completa(self) -> Tuple[bool, str, List[str]]:
        ok_espacio, msg_espacio = verificar_espacio_disco(
            os.path.dirname(self.base_dir), minimo_mb=5
        )
        if not ok_espacio:
            return False, msg_espacio, []

        os.makedirs(self.base_dir, exist_ok=True)
        creadas: List[str] = []
        rollback: List[str] = []

        try:
            for modulo, subcarpetas in _MODULOS.items():
                ruta_mod = self._ruta_modulo(modulo)
                if not os.path.exists(ruta_mod):
                    os.makedirs(ruta_mod)
                    rollback.append(ruta_mod)
                    creadas.append(modulo)
                for sub in subcarpetas:
                    ruta_sub = os.path.join(ruta_mod, sub)
                    if not os.path.exists(ruta_sub):
                        os.makedirs(ruta_sub)
                        rollback.append(ruta_sub)
                        creadas.append(f"{modulo}/{sub}")
            self._cache_ts = 0  # invalidar caché
            return True, f"{len(creadas)} carpetas creadas", creadas
        except Exception as e:
            logger.error(f"Error creando estructura: {e}. Haciendo rollback...")
            for ruta in reversed(rollback):
                try:
                    if os.path.isdir(ruta) and not os.listdir(ruta):
                        os.rmdir(ruta)
                except Exception:
                    pass
            return False, str(e), []

    def crear_carpeta_personalizada(self, modulo: str, nombre: str) -> Tuple[bool, str]:
        ok, msg = validar_nombre_carpeta(nombre)
        if not ok:
            return False, msg
        ruta_mod = self._ruta_modulo(modulo)
        if not os.path.isdir(ruta_mod):
            return False, f"Módulo '{modulo}' no existe"
        ruta_nueva = os.path.join(ruta_mod, nombre)
        ok_ruta, msg_ruta = validar_longitud_ruta(ruta_nueva)
        if not ok_ruta:
            return False, msg_ruta
        if os.path.exists(ruta_nueva):
            return False, "La carpeta ya existe"
        try:
            os.makedirs(ruta_nueva)
            self._cache_ts = 0
            return True, f"Carpeta '{nombre}' creada en {modulo}"
        except Exception as e:
            return False, str(e)

    def eliminar_carpeta(self, modulo: str, nombre: str) -> Tuple[bool, str]:
        ruta = os.path.join(self._ruta_modulo(modulo), nombre)
        if not os.path.isdir(ruta):
            return False, "Carpeta no encontrada"
        try:
            shutil.rmtree(ruta)
            self._cache_ts = 0
            return True, f"Carpeta '{nombre}' eliminada"
        except Exception as e:
            return False, str(e)

    def explorar_carpeta(self, modulo: str, sub: str = "", max_depth: int = 3) -> Dict:
        ruta_base = os.path.join(self._ruta_modulo(modulo), sub) if sub else self._ruta_modulo(modulo)
        if not os.path.isdir(ruta_base):
            return {"error": "Carpeta no encontrada"}

        def _listar(ruta: str, depth: int) -> List[Dict]:
            if depth > max_depth:
                return []
            items = []
            try:
                for nombre in sorted(os.listdir(ruta)):
                    ruta_item = os.path.join(ruta, nombre)
                    item: Dict[str, Any] = {"nombre": nombre}
                    if os.path.isdir(ruta_item):
                        item["tipo"] = "carpeta"
                        item["hijos"] = _listar(ruta_item, depth + 1)
                    else:
                        item["tipo"] = "archivo"
                        item["tamano"] = os.path.getsize(ruta_item)
                    items.append(item)
            except PermissionError:
                pass
            return items

        return {"ruta": ruta_base, "contenido": _listar(ruta_base, 1)}

    def obtener_estadisticas(self) -> Dict[str, Any]:
        ahora = time.time()
        if ahora - self._cache_ts < self._cache_ttl and self._cache:
            return self._cache

        stats: Dict[str, Any] = {"modulos": {}, "total_carpetas": 0, "total_archivos": 0, "total_bytes": 0}
        for modulo in _MODULOS:
            ruta_mod = self._ruta_modulo(modulo)
            m_stats: Dict[str, int] = {"carpetas": 0, "archivos": 0, "bytes": 0}
            if os.path.isdir(ruta_mod):
                for _, dirs, files in os.walk(ruta_mod):
                    m_stats["carpetas"] += len(dirs)
                    for fn in files:
                        m_stats["archivos"] += 1
                        try:
                            m_stats["bytes"] += os.path.getsize(os.path.join(_, fn))
                        except OSError:
                            pass
            stats["modulos"][modulo] = m_stats
            stats["total_carpetas"] += m_stats["carpetas"]
            stats["total_archivos"]  += m_stats["archivos"]
            stats["total_bytes"]     += m_stats["bytes"]

        self._cache    = stats
        self._cache_ts = ahora
        return stats

    def obtener_modulos(self) -> List[str]:
        return list(_MODULOS.keys())


file_manager = FileManager()
