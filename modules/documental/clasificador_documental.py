"""
modules/documental/clasificador_documental.py
Clasificador archivístico — fachada hacia core/document_classifier.py

El motor determinístico vive en core/document_classifier.py (RC5.5.x).
Este módulo es la fachada de alto nivel con funciones orientadas al operador
y el stub de TRD para RC6.0 (extensiones IA opcionales).

Basado en: Tabla de Retención Documental ASUACAP + OAIS ISO 14721:2012
"""

# ── Bandera de habilitación ───────────────────────────────────────────────────
ENABLED = True  # Motor determinístico activo desde RC5.5.x

# ── Metadatos del módulo ──────────────────────────────────────────────────────
MODULO_META = {
    "nombre":    "Clasificador Archivístico Automático",
    "nivel":     3,
    "version":   "0.1.0-scaffold",
    "baseline":  "RC6.0",
    "enabled":   ENABLED,
    "requiere":  ["scikit-learn>=1.3", "spacy>=3.7"],
}


def clasificar_documento(tipo_documental: str, asunto: str, area: str = "") -> dict:
    """
    Clasifica un documento según la TRD de ASUACAP.
    Delega al motor determinístico en core/document_classifier.py.

    Parámetros:
        tipo_documental: Tipo de documento (ej. "Resolución", "Acta", "Oficio")
        asunto: Resumen o asunto del documento
        area: Código de área (GA, GC, GF, GE, GL) — usado como fallback

    Retorna dict con: serie_codigo, serie_nombre, subserie, retencion_gestion,
                      retencion_central, disposicion_final, nivel_acceso, confianza
    """
    from core.document_classifier import clasificar_documento as _clf
    resultado = _clf(tipo_documental, asunto, area)
    return {"ok": True, "enabled": True, **resultado.to_dict()}


def sugerir_expediente(documento_id: int, asunto: str) -> dict:
    """
    Sugiere a qué expediente existente vincular un documento nuevo.
    RC5.5.x: búsqueda por palabras clave en expedientes abiertos.
    """
    from core.database_manager import get_db
    from core.document_classifier import determinar_serie
    conn = get_db()
    try:
        serie, _, _ = determinar_serie("", asunto)
        palabras = [p for p in asunto.split() if len(p) > 4][:5]
        if not palabras:
            return {"ok": True, "sugerencias": []}
        like_clause = " OR ".join(["e.descripcion LIKE ?" for _ in palabras])
        params = [f"%{p}%" for p in palabras]
        rows = conn.execute(f"""
            SELECT e.pk_expediente_id as id, e.nombre, e.codigo,
                   COUNT(*) as coincidencias
            FROM expedientes e
            WHERE e.estado NOT IN ('Cerrado','Archivado')
              AND ({like_clause})
            GROUP BY e.pk_expediente_id ORDER BY coincidencias DESC LIMIT 5
        """, params).fetchall()
        return {"ok": True, "sugerencias": [dict(r) for r in rows]}
    except Exception as e:
        return {"ok": False, "error": str(e), "sugerencias": []}
    finally:
        conn.close()


def calcular_fecha_eliminacion(fecha_radicacion: str, serie_codigo: str) -> dict:
    """
    Calcula la fecha de transferencia a Central y fecha de eliminación según TRD.
    """
    from core.document_classifier import determinar_retencion
    from datetime import date, timedelta
    try:
        ret = determinar_retencion(serie_codigo)
        fecha = date.fromisoformat(fecha_radicacion)
        fecha_central    = fecha.replace(year=fecha.year + ret["retencion_gestion"])
        fecha_eliminacion = fecha_central.replace(year=fecha_central.year + ret["retencion_central"])
        return {
            "ok": True,
            "serie_codigo":       serie_codigo,
            "retencion_gestion":  ret["retencion_gestion"],
            "retencion_central":  ret["retencion_central"],
            "disposicion_final":  ret["disposicion_final"],
            "fecha_transferencia_central":    fecha_central.isoformat(),
            "fecha_disposicion_final":        fecha_eliminacion.isoformat(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Tabla de Retención Documental — stub para RC6.0 ──────────────────────────
# Estructura: {codigo_trd: {serie, subserie, retencion_gestion, retencion_central, disposicion}}
TRD_ASUACAP_STUB = {
    "100.01": {"serie": "Actas", "subserie": "Actas de Junta Directiva",
               "retencion_gestion": 2, "retencion_central": 8, "disposicion": "Conservar"},
    "100.02": {"serie": "Actas", "subserie": "Actas de Asamblea",
               "retencion_gestion": 2, "retencion_central": 8, "disposicion": "Conservar"},
    "200.01": {"serie": "Contratos", "subserie": "Contratos de Prestación de Servicios",
               "retencion_gestion": 5, "retencion_central": 15, "disposicion": "Conservar"},
    "300.01": {"serie": "Correspondencia", "subserie": "Correspondencia Enviada",
               "retencion_gestion": 2, "retencion_central": 3, "disposicion": "Eliminar"},
    "300.02": {"serie": "Correspondencia", "subserie": "Correspondencia Recibida",
               "retencion_gestion": 2, "retencion_central": 3, "disposicion": "Eliminar"},
    "400.01": {"serie": "Informes", "subserie": "Informes de Gestión",
               "retencion_gestion": 2, "retencion_central": 8, "disposicion": "Conservar"},
    "500.01": {"serie": "PQRS", "subserie": "Peticiones, Quejas y Reclamos",
               "retencion_gestion": 2, "retencion_central": 3, "disposicion": "Eliminar"},
    "600.01": {"serie": "Proyectos", "subserie": "Proyectos de Infraestructura",
               "retencion_gestion": 5, "retencion_central": 10, "disposicion": "Conservar"},
}
