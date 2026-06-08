"""
core/forensic_saneamiento.py — Utilidades forenses para trazabilidad segura.
Proporciona normalizacion de fechas e IPs para cadenas de firma digital.
"""
import re, logging
from datetime import datetime
from flask import request as flask_request

logger = logging.getLogger("asuacap.forensic")


class SaneadorForense:
    @staticmethod
    def normalizar_fecha_estatica(dt=None):
        """Retorna timestamp ISO 8601 UTC con microsegundos para firma digital."""
        if dt is None:
            dt = datetime.utcnow()
        if isinstance(dt, str):
            return dt
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"

    @staticmethod
    def obtener_ip_segura(request=None):
        """Extrae IP real detras de proxies. Valida formato para evitar injection."""
        if request is None:
            try:
                request = flask_request
            except RuntimeError:
                return "0.0.0.0"
        # Encabezados de proxy en orden de confianza
        for header in ("X-Forwarded-For", "X-Real-IP", "CF-Connecting-IP"):
            val = request.headers.get(header, "").split(",")[0].strip()
            if val and SaneadorForense._ip_valida(val):
                return val
        return request.remote_addr or "0.0.0.0"

    @staticmethod
    def _ip_valida(ip):
        """Valida formato IPv4 o IPv6 basico para evitar injection en logs."""
        ipv4 = re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip)
        ipv6 = re.match(r"^[0-9a-fA-F:]{3,39}$", ip)
        return bool(ipv4 or ipv6)

    @staticmethod
    def sanitizar_para_log(texto, max_len=200):
        """Elimina caracteres de control y trunca para uso seguro en logs."""
        if not texto:
            return ""
        texto = re.sub(r"[\x00-\x1f\x7f]", " ", str(texto))
        return texto[:max_len]

    @staticmethod
    def generar_id_operacion():
        """Genera ID unico para correlacion de operaciones en auditoria."""
        import secrets
        return secrets.token_hex(8)
