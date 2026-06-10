"""
core/otp_manager.py — Gestion de OTP via WhatsApp (CallMeBot) para firmas digitales.
"""
import random, string, sqlite3, logging, requests
from datetime import datetime, timedelta
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from core.database_manager import get_db, registrar_log

logger = logging.getLogger("sigca.otp")

CARACTERES_OTP = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin O,0,I,1


def generar_codigo_otp(longitud: int = 6) -> str:
    """Genera codigo OTP alfanumerico sin caracteres confusos."""
    return "".join(random.choices(CARACTERES_OTP, k=longitud))


def enviar_whatsapp(numero: str, mensaje: str, api_key: str) -> tuple[bool, str]:
    """
    Envia mensaje por WhatsApp via CallMeBot.
    Retorna (exito, mensaje_error).
    """
    if not api_key:
        return False, "API Key de WhatsApp no configurada"
    numero_limpio = numero.strip().replace("+","").replace(" ","").replace("-","")
    url = (f"https://api.callmebot.com/whatsapp.php"
           f"?phone={numero_limpio}&text={requests.utils.quote(mensaje)}&apikey={api_key}")
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            return True, ""
        return False, f"HTTP {r.status_code}"
    except requests.RequestException as e:
        return False, str(e)


class OTPManager:
    """Gestiona el ciclo completo de OTP para un documento."""

    def __init__(self):
        self.api_key = self._obtener_api_key()

    def _obtener_api_key(self) -> str:
        try:
            conn = get_db()
            r = conn.execute("SELECT valor FROM configuracion WHERE clave='whatsapp_api_key'").fetchone()
            conn.close()
            return r["valor"] if r else ""
        except Exception:
            return ""

    def iniciar_autorizacion(self, registro_id: int, firmante_id: int) -> dict:
        """Genera OTP, lo guarda y lo envia por WhatsApp."""
        conn = get_db()
        try:
            # Datos del firmante
            firmante = conn.execute(
                "SELECT nombre_completo, cargo, whatsapp FROM firmantes WHERE pk_firmante_id=?",
                (firmante_id,)
            ).fetchone()
            if not firmante:
                return {"ok": False, "error": "Firmante no encontrado"}

            # Datos del documento
            doc = conn.execute(
                "SELECT codigo_completo, asunto_resumen FROM registro_central WHERE pk_registro_id=?",
                (registro_id,)
            ).fetchone()
            if not doc:
                return {"ok": False, "error": "Documento no encontrado"}

            codigo = generar_codigo_otp()
            expiracion = datetime.now() + timedelta(minutes=Config.OTP_EXPIRA_MINUTOS)

            # Invalidar OTPs anteriores del mismo par documento-firmante
            conn.execute("""
                UPDATE autorizaciones_otp SET estado='Expirado'
                WHERE fk_registro_id=? AND fk_firmante_id=? AND estado='Enviado'
            """, (registro_id, firmante_id))

            conn.execute("""
                INSERT INTO autorizaciones_otp
                (fk_registro_id,fk_firmante_id,codigo_otp,estado,fecha_expiracion)
                VALUES(?,?,?,'Enviado',?)
            """, (registro_id, firmante_id, codigo, expiracion.isoformat()))
            conn.commit()

            mensaje = (
                f"PARAGUASMJ: Sr(a). {firmante['cargo']}, "
                f"use el codigo OTP: {codigo} "
                f"para autorizar el documento {doc['codigo_completo']} "
                f"({doc['asunto_resumen'][:40]}). "
                f"Valido por {Config.OTP_EXPIRA_MINUTOS} minutos."
            )

            exito, error = enviar_whatsapp(firmante["whatsapp"], mensaje, self.api_key)

            if not exito:
                conn.execute("""
                    UPDATE autorizaciones_otp SET estado='Error', ultimo_error=?, intentos_envio=1
                    WHERE fk_registro_id=? AND fk_firmante_id=? AND codigo_otp=?
                """, (error, registro_id, firmante_id, codigo))
                conn.commit()
                logger.warning(f"OTP no enviado a {firmante['whatsapp']}: {error}")

            registrar_log("INFO","otp","sistema",f"OTP generado para doc {registro_id} firmante {firmante_id}")
            return {"ok": True, "enviado_whatsapp": exito, "error_wa": error if not exito else ""}

        except Exception as e:
            conn.rollback()
            logger.error(f"Error iniciando autorizacion: {e}")
            return {"ok": False, "error": str(e)}
        finally:
            conn.close()

    def verificar_otp(self, registro_id: int, firmante_id: int, codigo_ingresado: str) -> dict:
        """Verifica el codigo OTP ingresado por el firmante."""
        conn = get_db()
        try:
            otp = conn.execute("""
                SELECT pk_auth_id, codigo_otp, fecha_expiracion, estado
                FROM autorizaciones_otp
                WHERE fk_registro_id=? AND fk_firmante_id=? AND estado='Enviado'
                ORDER BY fecha_envio DESC LIMIT 1
            """, (registro_id, firmante_id)).fetchone()

            if not otp:
                return {"ok": False, "error": "No hay OTP pendiente para este firmante"}

            if datetime.now().isoformat() > otp["fecha_expiracion"]:
                conn.execute("UPDATE autorizaciones_otp SET estado='Expirado' WHERE pk_auth_id=?", (otp["pk_auth_id"],))
                conn.commit()
                return {"ok": False, "error": "El codigo OTP ha expirado"}

            if otp["codigo_otp"].upper() != codigo_ingresado.strip().upper():
                return {"ok": False, "error": "Codigo incorrecto"}

            conn.execute("""
                UPDATE autorizaciones_otp SET estado='Aprobado', fecha_aprobacion=CURRENT_TIMESTAMP
                WHERE pk_auth_id=?
            """, (otp["pk_auth_id"],))

            # Verificar si todos los firmantes obligatorios han aprobado
            aprobacion_completa = self._verificar_aprobacion_completa(conn, registro_id)
            if aprobacion_completa:
                conn.execute("UPDATE registro_central SET estado='Aprobado' WHERE pk_registro_id=?", (registro_id,))
                conn.execute("""
                    INSERT INTO seguimiento_documento(fk_registro_id,estado_actual,estado_anterior,usuario,observaciones)
                    VALUES(?,'Aprobado','En_autorizacion','sistema','Todos los firmantes aprobaron via OTP')
                """, (registro_id,))

            conn.commit()
            registrar_log("INFO","otp","sistema",f"OTP aprobado doc {registro_id} firmante {firmante_id}")
            return {"ok": True, "aprobacion_completa": aprobacion_completa}

        except Exception as e:
            conn.rollback()
            logger.error(f"Error verificando OTP: {e}")
            return {"ok": False, "error": str(e)}
        finally:
            conn.close()

    def _verificar_aprobacion_completa(self, conn, registro_id: int) -> bool:
        """Verifica si todos los firmantes obligatorios han aprobado."""
        doc = conn.execute(
            "SELECT tipo_documento FROM registro_central WHERE pk_registro_id=?",
            (registro_id,)
        ).fetchone()
        if not doc:
            return False
        obligatorios = conn.execute("""
            SELECT COUNT(*) as total FROM reglas_firmantes
            WHERE tipo_documento=? AND obligatorio=1
        """, (doc["tipo_documento"],)).fetchone()["total"]
        aprobados = conn.execute("""
            SELECT COUNT(DISTINCT fk_firmante_id) as total FROM autorizaciones_otp
            WHERE fk_registro_id=? AND estado='Aprobado'
        """, (registro_id,)).fetchone()["total"]
        return aprobados >= obligatorios > 0
