"""
utils/auditoria.py — Registro de auditoría con cadena HMAC-SHA256
"""
import hashlib, hmac, json, os, time, logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger("sigca.auditoria")

_CLAVE_HMAC = os.environ.get("AUDIT_SECRET", "PARAGUASMJ_AUDITORIA_2026_SECRET").encode()
_LOG_DIR    = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
_LOG_FILE   = os.path.join(_LOG_DIR, 'auditoria.jsonl')


def _firmar(entrada: dict) -> str:
    payload = json.dumps(entrada, ensure_ascii=False, sort_keys=True).encode()
    return hmac.new(_CLAVE_HMAC, payload, hashlib.sha256).hexdigest()


class AuditoriaManager:
    def __init__(self, log_file: str = _LOG_FILE):
        self.log_file = log_file
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        self._hash_anterior: Optional[str] = self._ultimo_hash()

    def _ultimo_hash(self) -> Optional[str]:
        try:
            if not os.path.exists(self.log_file):
                return None
            with open(self.log_file, 'rb') as f:
                lines = f.read().splitlines()
            for line in reversed(lines):
                if line.strip():
                    entry = json.loads(line)
                    return entry.get('hash_actual')
        except Exception:
            return None

    def registrar(self, accion: str, usuario: str = "sistema",
                  detalle: str = "", nivel: str = "INFO",
                  ip: str = "") -> bool:
        try:
            entrada = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "accion": accion,
                "usuario": usuario,
                "detalle": detalle,
                "nivel": nivel,
                "ip": ip,
                "hash_anterior": self._hash_anterior or "GENESIS",
            }
            firma = _firmar(entrada)
            entrada["hash_actual"] = firma
            entrada["firma_hmac"] = hmac.new(_CLAVE_HMAC, firma.encode(), hashlib.sha256).hexdigest()

            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entrada, ensure_ascii=False) + '\n')

            self._hash_anterior = firma
            return True
        except Exception as e:
            logger.error(f"Error registrando auditoría: {e}")
            return False

    def verificar_integridad(self) -> Dict[str, Any]:
        resultado = {"ok": True, "total": 0, "errores": [], "primer_error": None}
        try:
            if not os.path.exists(self.log_file):
                return resultado
            hash_prev = "GENESIS"
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    entrada = json.loads(line)
                    resultado["total"] += 1
                    if entrada.get("hash_anterior") != hash_prev:
                        resultado["ok"] = False
                        error = {"linea": i, "motivo": "cadena rota"}
                        resultado["errores"].append(error)
                        if not resultado["primer_error"]:
                            resultado["primer_error"] = error
                    hash_prev = entrada.get("hash_actual", "")
        except Exception as e:
            resultado["ok"] = False
            resultado["errores"].append({"motivo": str(e)})
        return resultado

    def obtener_ultimos(self, n: int = 100) -> List[Dict]:
        try:
            if not os.path.exists(self.log_file):
                return []
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = [l for l in f.read().splitlines() if l.strip()]
            return [json.loads(l) for l in lines[-n:]][::-1]
        except Exception:
            return []

    def exportar_reporte(self, destino: str) -> bool:
        try:
            entradas = self.obtener_ultimos(10000)
            with open(destino, 'w', encoding='utf-8') as f:
                json.dump({"generado": datetime.utcnow().isoformat(),
                           "total": len(entradas),
                           "entradas": entradas}, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error exportando auditoría: {e}")
            return False


auditoria_manager = AuditoriaManager()
