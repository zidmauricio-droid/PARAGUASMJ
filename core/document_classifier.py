"""
core/document_classifier.py — Clasificador archivístico determinístico RC5.5.x
Clasificación por reglas TRD: sin IA, sin LLM, 100% offline, auditable.

Funciones públicas:
    clasificar_documento(tipo_documento, asunto, area) -> ClasificacionDocumental
    determinar_serie(tipo_documento, asunto) -> str (codigo serie TRD)
    determinar_subserie(serie, tipo_documento, asunto) -> str
    determinar_retencion(serie) -> dict
    determinar_nivel_acceso(serie, tipo_documento) -> str
    enriquecer_registro(conn, registro_id) -> dict
"""

import re
import json
import os
import logging
import hashlib
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from typing import Optional

logger = logging.getLogger("sigca.classifier")

_TRD_JSON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "config", "trd.json")

# ── Estructura de resultado ───────────────────────────────────────────────────

@dataclass
class ClasificacionDocumental:
    serie_codigo:        str  = "OTR"
    serie_nombre:        str  = "OTROS"
    subserie:            str  = "General"
    retencion_gestion:   int  = 2
    retencion_central:   int  = 3
    disposicion_final:   str  = "eliminacion"
    nivel_acceso:        str  = "Restringido"
    fase_archivo:        str  = "Gestion"
    confianza:           str  = "REGLA"   # REGLA | AREA | DEFAULT
    motivo:              str  = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ── Carga TRD desde JSON ──────────────────────────────────────────────────────

def _cargar_trd() -> dict:
    try:
        if os.path.exists(_TRD_JSON):
            with open(_TRD_JSON, encoding="utf-8") as f:
                data = json.load(f)
            return {s["codigo"]: s for s in data.get("series", [])}
    except Exception as e:
        logger.warning(f"No se pudo cargar TRD JSON: {e}")
    return {}


_TRD_SERIES = _cargar_trd()


# ── Tabla de retenciones por serie ────────────────────────────────────────────
# Fallback si el JSON no tiene el campo. Basado en TRD vigente del acueducto.

_RETENCION_DEFAULT: dict[str, dict] = {
    "SUB":  {"retencion_gestion": 2,  "retencion_central": 3,  "disposicion_final": "conservacion_total"},
    "FIN":  {"retencion_gestion": 3,  "retencion_central": 7,  "disposicion_final": "conservacion_total"},
    "LEG":  {"retencion_gestion": 5,  "retencion_central": 15, "disposicion_final": "conservacion_total"},
    "PQRS": {"retencion_gestion": 1,  "retencion_central": 2,  "disposicion_final": "eliminacion"},
    "PRY":  {"retencion_gestion": 3,  "retencion_central": 7,  "disposicion_final": "conservacion_total"},
    "ADM":  {"retencion_gestion": 2,  "retencion_central": 5,  "disposicion_final": "eliminacion"},
    "OPS":  {"retencion_gestion": 2,  "retencion_central": 4,  "disposicion_final": "eliminacion"},
    "GOB":  {"retencion_gestion": 5,  "retencion_central": 20, "disposicion_final": "conservacion_total"},
    "OTR":  {"retencion_gestion": 2,  "retencion_central": 3,  "disposicion_final": "eliminacion"},
}

# ── Niveles de acceso por serie ───────────────────────────────────────────────

_ACCESO_SERIE: dict[str, str] = {
    "SUB":  "Restringido",
    "FIN":  "Confidencial",
    "LEG":  "Confidencial",
    "PQRS": "Restringido",
    "PRY":  "Publico",
    "ADM":  "Restringido",
    "OPS":  "Restringido",
    "GOB":  "Publico",
    "OTR":  "Restringido",
}

# ── Reglas de clasificación por tipo_documento ────────────────────────────────
# Orden importa: más específico primero.

_REGLAS_TIPO: list[tuple[re.Pattern, str, str]] = [
    # (patrón en tipo_documento o asunto, serie_codigo, subserie)
    (re.compile(r"petici[oó]n|queja|reclamo|sugerencia|pqrs|derecho\s+de\s+petici", re.I),
     "PQRS", "PQRS Ciudadana"),

    (re.compile(r"factura|cobro|recibo|estado\s+de\s+cuenta|cartera|pago|egreso|ingreso|caja\s+chica|presupuesto|balance|financier", re.I),
     "FIN", "Documentos Financieros"),

    (re.compile(r"contrato|convenio|acuerdo|licitaci[oó]n|orden\s+de\s+compra|p[oó]liza|garantía|escritura", re.I),
     "LEG", "Contratos y Convenios"),

    (re.compile(r"resoluci[oó]n|acuerdo|decreto|estatuto|reglamento|manual\s+de\s+funciones|manual\s+de\s+procedimientos", re.I),
     "GOB", "Normativa Institucional"),

    (re.compile(r"acta\s+de\s+(asamblea|junta|reuni[oó]n|directiva|comit[eé])", re.I),
     "GOB", "Actas de Gobierno"),

    (re.compile(r"proyecto|dise[ñn]o|plano|obra|construcci[oó]n|interventor[ií]a|informe\s+t[eé]cnico\s+de\s+(obra|proyecto)", re.I),
     "PRY", "Proyectos de Infraestructura"),

    (re.compile(r"suscriptor|usuario|afiliaci[oó]n|desafiliaci[oó]n|novedad\s+de\s+suscriptor|corte\s+de\s+servicio|reconexión", re.I),
     "SUB", "Gestión de Suscriptores"),

    (re.compile(r"informe\s+(de\s+)?(gesti[oó]n|actividades|laboral|operativo|t[eé]cnico)", re.I),
     "ADM", "Informes de Gestión"),

    (re.compile(r"certificado|constancia|paz\s+y\s+salvo|autorizaci[oó]n|permiso", re.I),
     "ADM", "Certificaciones"),

    (re.compile(r"circular|comunicado|oficio|memorando|correspondencia", re.I),
     "ADM", "Correspondencia"),

    (re.compile(r"falla|emergencia|reporte\s+(de\s+)?(falla|da[ñn]o|rotura|avería|novedades)", re.I),
     "OPS", "Reportes Operativos"),

    (re.compile(r"orden\s+de\s+trabajo|mantenimiento|inspecci[oó]n|revisi[oó]n\s+de\s+red", re.I),
     "OPS", "Órdenes de Trabajo"),

    (re.compile(r"acta\b(?!\s+de\s+(asamblea|junta|reuni[oó]n|directiva))", re.I),
     "ADM", "Actas Administrativas"),
]

# ── Reglas por área (área del registro_central) ───────────────────────────────

_AREA_A_SERIE: dict[str, str] = {
    "GF": "FIN",
    "GL": "LEG",
    "GA": "ADM",
    "GC": "SUB",
    "GE": "OPS",
}

_AREA_NOMBRES: dict[str, str] = {
    "GF": "Gerencia Financiera",
    "GL": "Gerencia Legal",
    "GA": "Gerencia Administrativa",
    "GC": "Gerencia Comercial",
    "GE": "Gerencia de Infraestructura",
}


# ── Funciones públicas ────────────────────────────────────────────────────────

@lru_cache(maxsize=512)
def _determinar_serie_cached(texto_norm: str) -> tuple:
    """Núcleo de clasificación con caché LRU — clave: texto normalizado hasta 200 chars (#8)."""
    for patron, serie, subserie in _REGLAS_TIPO:
        if patron.search(texto_norm):
            return serie, subserie, "REGLA"
    return "OTR", "General", "DEFAULT"


def determinar_serie(tipo_documento: str, asunto: str) -> tuple[str, str, str]:
    """
    Retorna (serie_codigo, subserie, confianza).
    confianza: 'REGLA' si hubo match por regla, 'DEFAULT' si no.
    Usa caché LRU de 512 entradas para entradas repetidas.
    """
    texto = f"{tipo_documento or ''} {asunto or ''}"
    # Normalizar y truncar para clave de caché reproducible
    texto_norm = re.sub(r"\s+", " ", texto).strip().lower()[:200]
    return _determinar_serie_cached(texto_norm)


def determinar_retencion(serie_codigo: str) -> dict:
    """Retorna dict con retencion_gestion, retencion_central, disposicion_final."""
    if serie_codigo in _TRD_SERIES:
        s = _TRD_SERIES[serie_codigo]
        return {
            "retencion_gestion":  s.get("retencion_gestion", 2),
            "retencion_central":  s.get("retencion_central", 3),
            "disposicion_final":  s.get("disposicion_final", "eliminacion"),
        }
    return _RETENCION_DEFAULT.get(serie_codigo, _RETENCION_DEFAULT["OTR"])


def determinar_nivel_acceso(serie_codigo: str, tipo_documento: str = "") -> str:
    """Retorna nivel de acceso: Publico | Restringido | Confidencial."""
    tipo_lower = (tipo_documento or "").lower()
    if re.search(r"contrase[ñn]a|clave|secreto|confidencial|sigiloso", tipo_lower):
        return "Confidencial"
    return _ACCESO_SERIE.get(serie_codigo, "Restringido")


def clasificar_documento(tipo_documento: str, asunto: str,
                          area: Optional[str] = None) -> ClasificacionDocumental:
    """
    Clasifica un documento según reglas TRD determinísticas.

    Parámetros:
        tipo_documento: tipo del documento (Resolución, Acta, Factura, etc.)
        asunto: texto del asunto/resumen del documento
        area: código de área (GA, GC, GF, GE, GL) — usado como fallback

    Retorna ClasificacionDocumental con todos los campos archivísticos.
    """
    serie_codigo, subserie, confianza = determinar_serie(tipo_documento, asunto)
    motivo = f"match:'{tipo_documento} {asunto[:40]}'"

    # Fallback por área si no hubo match por regla
    if confianza == "DEFAULT" and area and area in _AREA_A_SERIE:
        serie_codigo = _AREA_A_SERIE[area]
        subserie = f"Documentos de {_AREA_NOMBRES.get(area, area)}"
        confianza = "AREA"
        motivo = f"area:{area}"

    serie_nombre = "OTROS"
    if serie_codigo in _TRD_SERIES:
        serie_nombre = _TRD_SERIES[serie_codigo].get("nombre", serie_codigo)
    elif serie_codigo in _RETENCION_DEFAULT:
        _NOMBRES_INTERNOS = {
            "ADM": "ADMINISTRATIVO", "OPS": "OPERATIVO",
            "GOB": "GOBIERNO CORPORATIVO", "OTR": "OTROS",
        }
        serie_nombre = _NOMBRES_INTERNOS.get(serie_codigo, serie_codigo)

    ret = determinar_retencion(serie_codigo)
    acceso = determinar_nivel_acceso(serie_codigo, tipo_documento)

    return ClasificacionDocumental(
        serie_codigo      = serie_codigo,
        serie_nombre      = serie_nombre,
        subserie          = subserie,
        retencion_gestion = ret["retencion_gestion"],
        retencion_central = ret["retencion_central"],
        disposicion_final = ret["disposicion_final"],
        nivel_acceso      = acceso,
        fase_archivo      = "Gestion",
        confianza         = confianza,
        motivo            = motivo,
    )


def enriquecer_registro(conn, registro_id: int) -> dict:
    """
    Clasifica un registro ya guardado en BD y actualiza fk_trd_id si corresponde.
    Retorna dict con clasificacion + ok/error.
    No modifica estado ni fase — solo asigna serie TRD si falta.
    """
    try:
        row = conn.execute(
            "SELECT tipo_documento, asunto_resumen, area, fk_trd_id FROM registro_central WHERE pk_registro_id=?",
            (registro_id,)
        ).fetchone()
        if not row:
            return {"ok": False, "error": f"Registro {registro_id} no encontrado"}

        clf = clasificar_documento(
            tipo_documento = row["tipo_documento"] or "",
            asunto         = row["asunto_resumen"] or "",
            area           = row["area"],
        )

        # Buscar pk_trd_id en tabla trd por código de serie si no tiene asignado
        if row["fk_trd_id"] is None:
            trd_row = conn.execute(
                "SELECT pk_trd_id FROM trd WHERE nombre LIKE ? LIMIT 1",
                (f"%{clf.serie_nombre}%",)
            ).fetchone()
            if trd_row:
                conn.execute(
                    "UPDATE registro_central SET fk_trd_id=? WHERE pk_registro_id=?",
                    (trd_row["pk_trd_id"], registro_id)
                )
                conn.commit()

        return {"ok": True, "registro_id": registro_id, "clasificacion": clf.to_dict()}
    except Exception as e:
        logger.error(f"Error enriqueciendo registro {registro_id}: {e}")
        return {"ok": False, "error": str(e)}
