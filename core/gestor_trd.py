"""
core/gestor_trd.py — Gestor de Tabla de Retencion Documental (TRD)
Implementa verificacion de transferencias, simulacion y ejecucion.
"""
import json, os, logging
from datetime import date, datetime, timedelta
from core.database_manager import get_db

logger = logging.getLogger("sigca.trd")

_TRD_JSON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "config", "trd.json")


def _cargar_trd_json():
    try:
        if os.path.exists(_TRD_JSON):
            with open(_TRD_JSON, encoding="utf-8") as f:
                return json.load(f).get("series", [])
    except Exception as e:
        logger.error(f"Error cargando TRD JSON: {e}")
    return []


class GestorTRD:
    def verificar_transferencias_pendientes(self):
        """Retorna lista de documentos que superaron su retencion en gestion."""
        alertas = []
        conn = get_db()
        try:
            hoy = date.today().isoformat()
            rows = conn.execute("""
                SELECT r.pk_registro_id as id, r.codigo_completo as codigo,
                       r.asunto_resumen as asunto, r.fecha_radicacion,
                       r.fase_archivo, t.anos_gestion, t.nombre as serie
                FROM registro_central r
                LEFT JOIN trd t ON r.fk_trd_id = t.pk_trd_id
                WHERE r.fase_archivo = 'Gestion'
                  AND r.estado NOT IN ('Archivado','Rechazado')
                  AND t.anos_gestion IS NOT NULL
            """).fetchall()
            for r in rows:
                try:
                    fecha_rad = datetime.strptime(r["fecha_radicacion"], "%Y-%m-%d").date()
                    fecha_limite = fecha_rad.replace(year=fecha_rad.year + int(r["anos_gestion"]))
                    dias_rest = (fecha_limite - date.today()).days
                    if dias_rest <= 30:
                        alertas.append({
                            "id": r["id"], "codigo": r["codigo"],
                            "asunto": r["asunto"], "serie": r["serie"],
                            "dias_restantes": dias_rest,
                            "fecha_limite": fecha_limite.isoformat(),
                            "urgente": dias_rest <= 0,
                        })
                except (ValueError, TypeError):
                    pass
        except Exception as e:
            logger.error(f"Error verificando TRD: {e}")
        finally:
            conn.close()
        return alertas

    def simular_transferencia(self):
        """Simula cuantos documentos se transferirian sin ejecutar nada."""
        alertas = self.verificar_transferencias_pendientes()
        vencidos = [a for a in alertas if a["urgente"]]
        return {
            "total": len(alertas),
            "vencidos": len(vencidos),
            "proximos": len(alertas) - len(vencidos),
            "documentos": alertas[:10],
        }

    def ejecutar_transferencias(self, usuario="sistema"):
        """Transfiere documentos vencidos de Gestion a Central."""
        conn = get_db()
        try:
            alertas = self.verificar_transferencias_pendientes()
            vencidos = [a for a in alertas if a["urgente"]]
            if not vencidos:
                return {"ok": True, "total": 0, "mensaje": "Sin documentos pendientes"}
            hoy = date.today().isoformat()
            for doc in vencidos:
                conn.execute("""
                    UPDATE registro_central
                    SET fase_archivo='Central', fecha_ingreso_fase=?
                    WHERE pk_registro_id=?
                """, (hoy, doc["id"]))
                conn.execute("""
                    INSERT INTO seguimiento_documento
                    (fk_registro_id, estado_actual, usuario, observaciones)
                    VALUES (?, 'Archivado_Central', ?, 'Transferencia TRD automatica')
                """, (doc["id"], usuario))
            conn.commit()
            logger.info(f"TRD: {len(vencidos)} documentos transferidos por {usuario}")
            return {"ok": True, "total": len(vencidos)}
        except Exception as e:
            conn.rollback()
            logger.error(f"Error ejecutando TRD: {e}")
            return {"ok": False, "error": str(e), "total": 0}
        finally:
            conn.close()


gestor_trd = GestorTRD()
