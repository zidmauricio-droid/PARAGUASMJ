"""
core/scheduler_notificaciones.py
Tareas programadas: alertas de plazos, PQRS vencidas, backups.
Jerarquía de notificación: WhatsApp → Email → Log local.
"""
import logging
from datetime import datetime
from core.database_manager import get_db
from core.otp_manager import OTPManager, enviar_whatsapp
from core.backup_manager import crear_backup
from core.crypto_simple import descifrar

logger = logging.getLogger("sigca.scheduler")


def _notificar(destino_wa: str, destino_email: str, asunto: str, msg: str,
               api_key: str) -> str:
    """
    Intenta enviar notificación con fallback jerárquico:
    1. WhatsApp (si hay api_key y número)
    2. Email (si hay destinatario configurado)
    3. Log local (siempre como último recurso)
    Retorna: 'whatsapp' | 'email' | 'log'
    """
    # Intento 1: WhatsApp
    if api_key and destino_wa:
        try:
            ok, err = enviar_whatsapp(destino_wa, msg, api_key)
            if ok:
                return "whatsapp"
            logger.warning(f"WhatsApp fallido ({err}), intentando email...")
        except Exception as e:
            logger.warning(f"WhatsApp excepción ({e}), intentando email...")

    # Intento 2: Email
    if destino_email:
        try:
            from core.email_manager import enviar_correo
            if enviar_correo(destino_email, asunto, f"<p>{msg}</p>"):
                return "email"
            logger.warning("Email fallido, registrando en log local...")
        except Exception as e:
            logger.warning(f"Email excepción ({e}), registrando en log local...")

    # Intento 3: Log local — siempre disponible sin infraestructura
    logger.warning(f"[NOTIF_LOCAL] {asunto} | {msg}")
    return "log"


def _leer_config(conn, *claves) -> dict:
    """Lee múltiples claves de configuración en una sola consulta."""
    placeholders = ",".join("?" * len(claves))
    rows = conn.execute(
        f"SELECT clave, valor FROM configuracion WHERE clave IN ({placeholders})",
        claves
    ).fetchall()
    return {r["clave"]: r["valor"] for r in rows}


def verificar_plazos_documentos():
    """
    Envia alertas para documentos cuyo plazo inicio notificaciones ya venció.
    Jerarquía: WhatsApp → Email → Log.
    """
    conn = get_db()
    try:
        hoy = datetime.now().date().isoformat()
        cfg = _leer_config(conn, "whatsapp_api_key", "correo_notificaciones")
        api_key        = descifrar(cfg.get("whatsapp_api_key", "") or "")
        correo_notif   = cfg.get("correo_notificaciones", "")

        # Notificaciones iniciales
        docs = conn.execute("""
            SELECT p.*, r.codigo_completo, r.asunto_resumen, r.tipo_documento
            FROM plazos_documento p
            JOIN registro_central r ON p.fk_registro_id=r.pk_registro_id
            WHERE p.fecha_inicio_notificaciones<=? AND p.notificacion_inicial_enviada=0
              AND r.estado NOT IN ('Aprobado','Archivado','Rechazado')
        """, (hoy,)).fetchall()

        for doc in docs:
            responsables = conn.execute("""
                SELECT DISTINCT f.nombre_completo, f.cargo, f.whatsapp,
                       COALESCE(f.email,'') as email
                FROM acciones_pendientes a
                JOIN firmantes f ON a.responsable_id=f.pk_firmante_id
                WHERE a.fk_registro_id=? AND a.estado='Pendiente'
            """, (doc["fk_registro_id"],)).fetchall()

            for resp in responsables:
                asunto = f"SIGCA: Documento {doc['codigo_completo']} requiere acción"
                msg = (f"Sr(a). {resp['cargo']}, el documento {doc['codigo_completo']} - "
                       f"{doc['asunto_resumen'][:40]} requiere su atención.")
                canal = _notificar(
                    resp["whatsapp"], resp.get("email") or correo_notif,
                    asunto, msg, api_key
                )
                logger.info(f"Notif {doc['codigo_completo']} → {resp['cargo']} via {canal}")

            conn.execute("""
                UPDATE plazos_documento
                SET notificacion_inicial_enviada=1, ultimo_recordatorio=date('now')
                WHERE pk_plazo_id=?
            """, (doc["pk_plazo_id"],))

        # Recordatorios periódicos
        pendientes = conn.execute("""
            SELECT p.*, r.codigo_completo, r.asunto_resumen
            FROM plazos_documento p
            JOIN registro_central r ON p.fk_registro_id=r.pk_registro_id
            WHERE p.notificacion_inicial_enviada=1
              AND julianday(date('now'))-julianday(p.ultimo_recordatorio)>=p.frecuencia_recordatorio
              AND r.estado NOT IN ('Aprobado','Archivado','Rechazado')
        """).fetchall()

        for doc in pendientes:
            responsables = conn.execute("""
                SELECT DISTINCT f.whatsapp, f.cargo, COALESCE(f.email,'') as email
                FROM acciones_pendientes a
                JOIN firmantes f ON a.responsable_id=f.pk_firmante_id
                WHERE a.fk_registro_id=? AND a.estado='Pendiente'
            """, (doc["fk_registro_id"],)).fetchall()
            for resp in responsables:
                asunto = f"RECORDATORIO SIGCA: {doc['codigo_completo']} pendiente"
                msg = (f"Documento {doc['codigo_completo']} pendiente de su autorización.")
                _notificar(resp["whatsapp"], resp.get("email") or correo_notif,
                           asunto, msg, api_key)
            conn.execute(
                "UPDATE plazos_documento SET ultimo_recordatorio=date('now') WHERE pk_plazo_id=?",
                (doc["pk_plazo_id"],)
            )

        conn.commit()
        logger.info(f"Verificacion plazos: {len(docs)} docs notificados")
    except Exception as e:
        logger.error(f"Error en verificar_plazos: {e}")
    finally:
        conn.close()


def verificar_pqrs_vencidas():
    """
    Alerta sobre PQRS próximas a vencer o ya vencidas.
    Jerarquía: WhatsApp → Email → Log.
    """
    conn = get_db()
    try:
        cfg = _leer_config(conn, "whatsapp_api_key", "correo_notificaciones")
        api_key      = descifrar(cfg.get("whatsapp_api_key", "") or "")
        correo_notif = cfg.get("correo_notificaciones", "")

        vencidas = conn.execute("""
            SELECT p.pk_pqr_id, r.codigo_completo, p.fecha_limite, c.razon_social,
                   COALESCE(c.whatsapp,'') as whatsapp,
                   COALESCE(c.correo,'') as correo
            FROM pqrs p
            JOIN registro_central r ON p.fk_registro_id=r.pk_registro_id
            JOIN contactos c ON p.fk_suscriptor_id=c.pk_contacto_id
            WHERE p.fecha_limite<=date('now','+2 days')
              AND p.estado_pqr NOT IN ('Respondida','Cerrada')
        """).fetchall()

        for pqr in vencidas:
            asunto = f"⚠️ PQRS {pqr['codigo_completo']} vence {pqr['fecha_limite']}"
            msg = (f"PQRS {pqr['codigo_completo']} vence el {pqr['fecha_limite']}. "
                   f"Suscriptor: {pqr['razon_social']}. Gestione a la brevedad.")
            canal = _notificar(
                pqr["whatsapp"], pqr.get("correo") or correo_notif,
                asunto, msg, api_key
            )
            logger.warning(f"PQRS próxima a vencer: {pqr['codigo_completo']} "
                           f"— {pqr['fecha_limite']} | Notif via {canal}")
    except Exception as e:
        logger.error(f"Error verificando PQRS: {e}")
    finally:
        conn.close()


def tarea_diaria_completa():
    """Ejecuta todas las tareas programadas diarias."""
    logger.info("=== Inicio tareas programadas diarias ===")
    verificar_plazos_documentos()
    verificar_pqrs_vencidas()
    crear_backup()
    logger.info("=== Tareas programadas completadas ===")
