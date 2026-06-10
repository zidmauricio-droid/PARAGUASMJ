"""
core/scheduler_notificaciones.py
Tareas programadas: alertas de plazos, PQRS vencidas, backups.
"""
import logging
from datetime import datetime
from core.database_manager import get_db
from core.otp_manager import OTPManager, enviar_whatsapp
from core.backup_manager import crear_backup

logger = logging.getLogger("sigca.scheduler")


def verificar_plazos_documentos():
    """
    Envia alertas WhatsApp/email para documentos cuyo plazo inicio
    notificaciones ya vencio y no han sido notificados.
    """
    conn = get_db()
    try:
        hoy = datetime.now().date().isoformat()
        api_key = conn.execute(
            "SELECT valor FROM configuracion WHERE clave='whatsapp_api_key'"
        ).fetchone()
        api_key = api_key["valor"] if api_key else ""

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
                SELECT DISTINCT f.nombre_completo, f.cargo, f.whatsapp
                FROM acciones_pendientes a
                JOIN firmantes f ON a.responsable_id=f.pk_firmante_id
                WHERE a.fk_registro_id=? AND a.estado='Pendiente'
            """, (doc["fk_registro_id"],)).fetchall()

            for resp in responsables:
                if resp["whatsapp"] and api_key:
                    msg = (f"PARAGUASMJ: Sr(a). {resp['cargo']}, "
                           f"el documento {doc['codigo_completo']} - "
                           f"{doc['asunto_resumen'][:40]} requiere su atencion.")
                    enviar_whatsapp(resp["whatsapp"], msg, api_key)

            conn.execute("""
                UPDATE plazos_documento
                SET notificacion_inicial_enviada=1, ultimo_recordatorio=date('now')
                WHERE pk_plazo_id=?
            """, (doc["pk_plazo_id"],))

        # Recordatorios periodicos
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
                SELECT DISTINCT f.whatsapp, f.cargo
                FROM acciones_pendientes a
                JOIN firmantes f ON a.responsable_id=f.pk_firmante_id
                WHERE a.fk_registro_id=? AND a.estado='Pendiente'
            """, (doc["fk_registro_id"],)).fetchall()
            for resp in responsables:
                if resp["whatsapp"] and api_key:
                    msg = (f"RECORDATORIO SIGCA: Documento {doc['codigo_completo']} "
                           f"pendiente de su autorizacion.")
                    enviar_whatsapp(resp["whatsapp"], msg, api_key)
            conn.execute("""
                UPDATE plazos_documento SET ultimo_recordatorio=date('now')
                WHERE pk_plazo_id=?
            """, (doc["pk_plazo_id"],))

        conn.commit()
        logger.info(f"Verificacion plazos completada. Docs notificados: {len(docs)}")
    except Exception as e:
        logger.error(f"Error en verificar_plazos: {e}")
    finally:
        conn.close()


def verificar_pqrs_vencidas():
    """Alerta sobre PQRS proximas a vencer o ya vencidas — envía WhatsApp si hay API key."""
    conn = get_db()
    try:
        api_key = conn.execute(
            "SELECT valor FROM configuracion WHERE clave='whatsapp_api_key'"
        ).fetchone()
        api_key = api_key["valor"] if api_key else ""

        vencidas = conn.execute("""
            SELECT p.pk_pqr_id, r.codigo_completo, p.fecha_limite, c.razon_social,
                   c.whatsapp
            FROM pqrs p
            JOIN registro_central r ON p.fk_registro_id=r.pk_registro_id
            JOIN contactos c ON p.fk_suscriptor_id=c.pk_contacto_id
            WHERE p.fecha_limite<=date('now','+2 days')
              AND p.estado_pqr NOT IN ('Respondida','Cerrada')
        """).fetchall()

        for pqr in vencidas:
            logger.warning(
                f"PQRS proxima a vencer: {pqr['codigo_completo']} — {pqr['fecha_limite']}"
            )
            if api_key and pqr["whatsapp"]:
                msg = (f"⚠️ PQRS {pqr['codigo_completo']} vence el {pqr['fecha_limite']}. "
                       f"Suscriptor: {pqr['razon_social']}. Por favor gestione a la brevedad.")
                try:
                    enviar_whatsapp(pqr["whatsapp"], msg, api_key)
                except Exception as we:
                    logger.error(f"Error enviando alerta PQRS {pqr['codigo_completo']}: {we}")
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
