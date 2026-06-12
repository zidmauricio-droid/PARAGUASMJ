"""
modules/indexer.py — Índice Maestro de Expedientes RC5.5.x
Reconstruye el índice expediente→documentos desde eventos de BD.
Sin IA, sin cache externo — lectura directa de registro_central.

API:
    reconstruir_indice(conn)     → dict índice completo
    indice_expediente(conn, id)  → dict expediente con documentos
    estadisticas_indice(conn)    → dict resumen numérico
    buscar_en_expedientes(conn, q) → list expedientes coincidentes
"""
import logging
from datetime import date

logger = logging.getLogger("sigca.indexer")


def reconstruir_indice(conn) -> dict:
    """
    Reconstruye el índice maestro completo de expedientes.
    Retorna dict {expediente_id: {expediente, documentos, total_folios, series}}.
    """
    try:
        expedientes = conn.execute("""
            SELECT pk_expediente_id as id, codigo_expediente as codigo,
                   nombre, descripcion, estado, fecha_apertura, fecha_cierre
            FROM expedientes
            ORDER BY codigo_expediente
        """).fetchall()

        indice = {}
        for exp in expedientes:
            eid = exp["id"]
            docs = conn.execute("""
                SELECT r.pk_registro_id as id, r.codigo_completo as codigo,
                       r.asunto_resumen as asunto, r.tipo_documento,
                       r.fecha_radicacion, r.estado, r.folio_inicio, r.folio_fin,
                       t.nombre as serie_nombre
                FROM registro_central r
                LEFT JOIN trd t ON r.fk_trd_id = t.pk_trd_id
                WHERE r.fk_expediente_id = ?
                ORDER BY r.folio_inicio NULLS LAST, r.fecha_radicacion
            """, (eid,)).fetchall()

            total_folios = sum(
                (d["folio_fin"] - d["folio_inicio"] + 1)
                for d in docs
                if d["folio_inicio"] is not None and d["folio_fin"] is not None
            )
            series = list({d["serie_nombre"] for d in docs if d["serie_nombre"]})

            indice[eid] = {
                "expediente":   dict(exp),
                "documentos":   [dict(d) for d in docs],
                "total_docs":   len(docs),
                "total_folios": total_folios,
                "series":       series,
                "alerta_folios": total_folios > 200,
            }
        return {"ok": True, "total_expedientes": len(indice), "indice": indice}
    except Exception as e:
        logger.error(f"Error reconstruyendo índice: {e}")
        return {"ok": False, "error": str(e), "indice": {}}


def indice_expediente(conn, expediente_id: int) -> dict:
    """
    Retorna el índice completo de un expediente específico con todos sus documentos.
    """
    try:
        exp = conn.execute(
            "SELECT * FROM expedientes WHERE pk_expediente_id=?", (expediente_id,)
        ).fetchone()
        if not exp:
            return {"ok": False, "error": f"Expediente {expediente_id} no encontrado"}

        docs = conn.execute("""
            SELECT r.pk_registro_id as id, r.codigo_completo as codigo,
                   r.asunto_resumen as asunto, r.tipo_documento,
                   r.fecha_radicacion, r.estado, r.folio_inicio, r.folio_fin,
                   r.creado_por, t.nombre as serie_nombre,
                   t.disposicion_final
            FROM registro_central r
            LEFT JOIN trd t ON r.fk_trd_id = t.pk_trd_id
            WHERE r.fk_expediente_id = ?
            ORDER BY r.folio_inicio NULLS LAST, r.fecha_radicacion
        """, (expediente_id,)).fetchall()

        total_folios = sum(
            (d["folio_fin"] - d["folio_inicio"] + 1)
            for d in docs
            if d["folio_inicio"] is not None and d["folio_fin"] is not None
        )
        docs_sin_folio = [d["codigo"] for d in docs if d["folio_inicio"] is None]
        series = {}
        for d in docs:
            s = d["serie_nombre"] or "Sin clasificar"
            series[s] = series.get(s, 0) + 1

        return {
            "ok":            True,
            "expediente":    dict(exp),
            "documentos":    [dict(d) for d in docs],
            "total_docs":    len(docs),
            "total_folios":  total_folios,
            "series":        series,
            "alerta_folios": total_folios > 200,
            "docs_sin_folio": docs_sin_folio,
            "integridad":    "ok" if not docs_sin_folio else f"{len(docs_sin_folio)} docs sin folio",
        }
    except Exception as e:
        logger.error(f"Error indexando expediente {expediente_id}: {e}")
        return {"ok": False, "error": str(e)}


def estadisticas_indice(conn) -> dict:
    """
    Retorna resumen numérico del índice sin cargar todos los documentos.
    """
    try:
        total_exp    = conn.execute("SELECT COUNT(*) FROM expedientes").fetchone()[0]
        abiertos     = conn.execute("SELECT COUNT(*) FROM expedientes WHERE estado NOT IN ('Cerrado','Archivado')").fetchone()[0]
        sin_docs     = conn.execute("""
            SELECT COUNT(*) FROM expedientes e
            WHERE NOT EXISTS (SELECT 1 FROM registro_central r WHERE r.fk_expediente_id=e.pk_expediente_id)
        """).fetchone()[0]
        docs_sin_exp = conn.execute(
            "SELECT COUNT(*) FROM registro_central WHERE fk_expediente_id IS NULL AND estado NOT IN ('Borrador','Rechazado')"
        ).fetchone()[0]
        sobre_limite = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT fk_expediente_id, SUM(folio_fin - folio_inicio + 1) AS folios
                FROM registro_central
                WHERE fk_expediente_id IS NOT NULL AND folio_inicio IS NOT NULL AND folio_fin IS NOT NULL
                GROUP BY fk_expediente_id HAVING folios > 200
            )
        """).fetchone()[0]
        return {
            "ok":              True,
            "total_expedientes": total_exp,
            "expedientes_abiertos": abiertos,
            "expedientes_sin_documentos": sin_docs,
            "documentos_sin_expediente": docs_sin_exp,
            "expedientes_sobre_limite_folios": sobre_limite,
            "fecha_consulta": date.today().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error en estadísticas de índice: {e}")
        return {"ok": False, "error": str(e)}


def buscar_en_expedientes(conn, query: str, limite: int = 20) -> list:
    """
    Busca expedientes por código, nombre o descripción.
    Retorna lista de expedientes con conteo de documentos.
    """
    if not query or len(query.strip()) < 2:
        return []
    q = f"%{query.strip()}%"
    try:
        rows = conn.execute("""
            SELECT e.pk_expediente_id as id, e.codigo_expediente as codigo,
                   e.nombre, e.estado,
                   COUNT(r.pk_registro_id) as total_docs
            FROM expedientes e
            LEFT JOIN registro_central r ON r.fk_expediente_id = e.pk_expediente_id
            WHERE e.codigo_expediente LIKE ? OR e.nombre LIKE ? OR e.descripcion LIKE ?
            GROUP BY e.pk_expediente_id
            ORDER BY e.codigo_expediente
            LIMIT ?
        """, (q, q, q, limite)).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error buscando en expedientes: {e}")
        return []
