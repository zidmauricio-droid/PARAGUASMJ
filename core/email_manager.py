"""
core/email_manager.py
Envio de correos institucionales via SMTP.
Fuente: PROGRAMA_1.doc - seccion correo a CAR con PUEAA adjunto.
PROGRAMA_2.doc - notificaciones PQRS y reportes.
"""
import smtplib, logging, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database_manager import get_db, registrar_log

logger = logging.getLogger("sigca.email")


def _obtener_config_smtp() -> dict:
    """Lee config SMTP desde BD."""
    conn = get_db()
    rows = conn.execute("""
        SELECT clave, valor FROM configuracion
        WHERE clave IN ('email_smtp_host','email_smtp_port','email_usuario','email_password','correo_oficial','nombre_asociacion')
    """).fetchall()
    conn.close()
    return {r["clave"]: r["valor"] for r in rows}


def enviar_correo(destinatario: str, asunto: str, cuerpo_html: str,
                  archivos_adjuntos: list = None, remitente_nombre: str = "PARAGUASMJ") -> bool:
    """
    Envia un correo via SMTP con soporte de adjuntos.
    Guarda historial en notificaciones_historial.

    Args:
        destinatario: correo destino (ej: sau@car.gov.co)
        asunto: asunto del correo
        cuerpo_html: cuerpo en HTML
        archivos_adjuntos: lista de rutas de archivos a adjuntar
        remitente_nombre: nombre visible del remitente
    """
    cfg = _obtener_config_smtp()
    usuario = cfg.get("email_usuario", "")
    password = cfg.get("email_password", "")
    host = cfg.get("email_smtp_host", "smtp.gmail.com")
    port = int(cfg.get("email_smtp_port", 587))
    correo_from = cfg.get("correo_oficial", usuario)
    nombre_asoc = cfg.get("nombre_asociacion", "SIGCA")

    estado = "enviado"
    error_msg = ""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"]    = f"{nombre_asoc} <{correo_from}>"
        msg["To"]      = destinatario

        # Cuerpo HTML
        msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

        # Adjuntos
        for ruta in (archivos_adjuntos or []):
            if os.path.exists(ruta):
                with open(ruta, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition",
                                f"attachment; filename={os.path.basename(ruta)}")
                msg.attach(part)

        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            if usuario and password:
                server.login(usuario, password)
            server.sendmail(correo_from, [destinatario], msg.as_string())

        logger.info(f"Correo enviado a {destinatario}: {asunto}")

    except Exception as e:
        estado = "error"
        error_msg = str(e)
        logger.error(f"Error enviando correo a {destinatario}: {e}")

    # Guardar historial
    try:
        conn = get_db()
        conn.execute("""
            INSERT INTO notificaciones_historial
            (destinatario, canal, mensaje, estado_envio, error_mensaje)
            VALUES (?, 'email', ?, ?, ?)
        """, (destinatario, f"{asunto[:80]}", estado, error_msg))
        conn.commit(); conn.close()
    except Exception:
        pass

    return estado == "enviado"


def enviar_pueaa_car(pdf_path: str, correo_car: str = "sau@car.gov.co") -> bool:
    """
    Envia el PUEAA adjunto a la CAR por correo.
    Fuente: PROGRAMA_1.doc - seccion 6, correo a CAR.
    """
    cfg = _obtener_config_smtp()
    nombre = cfg.get("nombre_asociacion", "SIGCA")
    anio   = datetime.now().year
    cuerpo = f"""
    <html><body style="font-family:Arial,sans-serif;font-size:10pt;">
    <p>Señores<br><strong>Corporación Autónoma Regional de Cundinamarca - CAR</strong><br>
    Oficina Regional Gualivá</p>

    <p>Reciban un cordial saludo.</p>

    <p>Por medio del presente correo, la <strong>{nombre}</strong>, identificada con
    NIT 832.001.389-2, con domicilio en el Caserío El Puente, Villeta, Cundinamarca,
    remite para su radicación oficial el <strong>Plan de Uso Eficiente y Ahorro del Agua
    (PUEAA) actualizado — Vigencia {anio}</strong>, dando cumplimiento a lo establecido
    en la Ley 373 de 1997 y la Resolución CAR 1257/2018.</p>

    <p>Adjunto encontrarán el documento en formato PDF con todas las plantillas
    diligenciadas (Plantillas 1 a 15).</p>

    <p>Quedamos atentos a cualquier observación o requerimiento adicional.</p>

    <p>Cordialmente,<br>
    <strong>Junta Directiva</strong><br>
    aacueductoelpuente@yahoo.com<br>
    Villeta, Cundinamarca</p>
    </body></html>
    """
    return enviar_correo(
        destinatario=correo_car,
        asunto=f"PUEAA {nombre} — Vigencia {anio} — Radicación",
        cuerpo_html=cuerpo,
        archivos_adjuntos=[pdf_path] if pdf_path else []
    )


def notificar_pqrs_estado(pqr_id: int) -> bool:
    """
    Notifica al suscriptor cuando su PQRS cambia de estado.
    Fuente: PROGRAMA_2.doc - seccion 1 PQRS.
    """
    conn = get_db()
    try:
        pqr = conn.execute("""
            SELECT p.*, r.codigo_completo, r.fecha_radicacion,
                   c.razon_social, c.correo
            FROM pqrs p
            JOIN registro_central r ON p.fk_registro_id=r.pk_registro_id
            JOIN contactos c ON p.fk_suscriptor_id=c.pk_contacto_id
            WHERE p.pk_pqr_id=?
        """, (pqr_id,)).fetchone()
        if not pqr or not pqr["correo"]:
            return False

        cfg = _obtener_config_smtp()
        estados_msg = {
            "Recibida":   "ha sido recibida y registrada en nuestro sistema",
            "En_tramite": "está siendo estudiada por nuestro equipo",
            "Respondida": "ha sido respondida. Puede consultar la respuesta en nuestras oficinas",
            "Cerrada":    "ha sido cerrada satisfactoriamente",
        }
        msg_estado = estados_msg.get(pqr["estado_pqr"], "ha cambiado de estado")

        cuerpo = f"""
        <html><body style="font-family:Arial,sans-serif;font-size:10pt;">
        <p>Estimado(a) <strong>{pqr['razon_social']}</strong>,</p>
        <p>Le informamos que su {pqr['tipo_pqr']} radicada con el número
        <strong>{pqr['codigo_completo']}</strong> {msg_estado}.</p>
        {'<p><strong>Respuesta:</strong> ' + pqr['respuesta_definitiva'] + '</p>' if pqr.get('respuesta_definitiva') else ''}
        <p>Gracias por comunicarse con nosotros.</p>
        <p><em>{cfg.get("nombre_asociacion","SIGCA")} — Caserío El Puente, Villeta, Cundinamarca</em></p>
        </body></html>
        """
        return enviar_correo(
            destinatario=pqr["correo"],
            asunto=f"Actualización PQRS {pqr['codigo_completo']} — {cfg.get('nombre_asociacion','SIGCA')}",
            cuerpo_html=cuerpo
        )
    except Exception as e:
        logger.error(f"Error notificando PQRS {pqr_id}: {e}")
        return False
    finally:
        conn.close()
