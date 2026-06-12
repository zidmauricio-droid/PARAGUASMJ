"""
modules/documental/clasificador_documental.py
Clasificador archivístico automático — Nivel 3 (RC6.0+)

ESTADO: DESACTIVADO (enabled = False)
Este módulo es un scaffold para RC6.0. No se conecta al núcleo RC5.5.
No importar desde routes/ ni core/ hasta que enabled=True en RC6.0.

Basado en: Tabla de Retención Documental ASUACAP + OAIS ISO 14721:2012
"""

# ── Bandera de habilitación ───────────────────────────────────────────────────
ENABLED = False  # RC6.0: cambiar a True tras 90 días de operación estable RC5.5

# ── Metadatos del módulo ──────────────────────────────────────────────────────
MODULO_META = {
    "nombre":    "Clasificador Archivístico Automático",
    "nivel":     3,
    "version":   "0.1.0-scaffold",
    "baseline":  "RC6.0",
    "enabled":   ENABLED,
    "requiere":  ["scikit-learn>=1.3", "spacy>=3.7"],
}


def clasificar_documento(asunto: str, dependencia: str, tipo_documental: str) -> dict:
    """
    Clasifica un documento según la TRD de ASUACAP.

    Parámetros:
        asunto: Resumen o asunto del documento
        dependencia: Dependencia productora (ej. "Gerencia", "Fontanería")
        tipo_documental: Tipo de documento (ej. "Resolución", "Acta", "Oficio")

    Retorna dict con: serie, subserie, codigo_trd, retencion_archivo_gestion,
                      retencion_archivo_central, disposicion_final

    Estado: SCAFFOLD — retorna siempre NOT_ENABLED en RC5.5
    """
    if not ENABLED:
        return {
            "ok":     False,
            "error":  "ClasificadorDocumental no habilitado (RC6.0)",
            "enabled": False,
        }

    # ── Implementación RC6.0 (pendiente) ─────────────────────────────────────
    # 1. Preprocesar texto: normalización, stopwords español
    # 2. Modelo TF-IDF entrenado con TRD institucional
    # 3. Clasificador kNN o Naive Bayes sobre series documentales
    # 4. Mapeo a codigo_trd (ej. 100.01 Actas, 200.03 Contratos)
    # 5. Retención según TRD: años en gestión + años en central + disposición
    raise NotImplementedError("ClasificadorDocumental pendiente RC6.0")


def sugerir_expediente(documento_id: int, asunto: str) -> dict:
    """
    Sugiere a qué expediente existente vincular un documento nuevo.

    Estado: SCAFFOLD — RC6.0
    """
    if not ENABLED:
        return {"ok": False, "error": "ClasificadorDocumental no habilitado (RC6.0)", "enabled": False}
    raise NotImplementedError("sugerir_expediente pendiente RC6.0")


def calcular_fecha_eliminacion(fecha_radicacion: str, codigo_trd: str) -> dict:
    """
    Calcula la fecha de eliminación / transferencia según TRD.

    Estado: SCAFFOLD — RC6.0
    """
    if not ENABLED:
        return {"ok": False, "error": "ClasificadorDocumental no habilitado (RC6.0)", "enabled": False}
    raise NotImplementedError("calcular_fecha_eliminacion pendiente RC6.0")


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
