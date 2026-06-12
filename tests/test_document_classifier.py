"""
tests/test_document_classifier.py — Clasificador archivístico determinístico RC5.5.x
Cobertura: reglas TRD, retenciones, niveles de acceso, fallback por área.
"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_classifier import (
    clasificar_documento,
    determinar_serie,
    determinar_retencion,
    determinar_nivel_acceso,
    ClasificacionDocumental,
)


# ── determinar_serie ─────────────────────────────────────────────────────────

class TestDeterminarSerie:
    def test_pqrs_por_tipo(self):
        serie, subserie, conf = determinar_serie("Petición", "Solicitud de información")
        assert serie == "PQRS"
        assert conf == "REGLA"

    def test_pqrs_por_asunto(self):
        serie, _, conf = determinar_serie("Oficio", "Queja por corte de servicio")
        assert serie == "PQRS"
        assert conf == "REGLA"

    def test_financiero_factura(self):
        serie, subserie, _ = determinar_serie("Factura", "Cobro servicio acueducto")
        assert serie == "FIN"

    def test_financiero_presupuesto(self):
        serie, _, _ = determinar_serie("Informe", "Presupuesto 2026 aprobado")
        assert serie == "FIN"

    def test_legal_contrato(self):
        serie, subserie, _ = determinar_serie("Contrato", "Prestación de servicios fontanería")
        assert serie == "LEG"
        assert "Contratos" in subserie

    def test_legal_convenio(self):
        serie, _, _ = determinar_serie("Convenio", "Acuerdo con Alcaldía Villeta")
        assert serie == "LEG"

    def test_gobierno_resolucion(self):
        serie, subserie, _ = determinar_serie("Resolución", "Resolución administrativa 01")
        assert serie == "GOB"

    def test_gobierno_acta_junta(self):
        serie, subserie, _ = determinar_serie("Acta", "Acta de Junta Directiva No. 5")
        assert serie == "GOB"
        assert "Actas" in subserie

    def test_proyecto_infraestructura(self):
        serie, _, _ = determinar_serie("Informe técnico", "Proyecto de construcción red de distribución")
        assert serie == "PRY"

    def test_suscriptor(self):
        serie, _, _ = determinar_serie("Solicitud", "Afiliación nuevo suscriptor zona norte")
        assert serie == "SUB"

    def test_operativo_falla(self):
        serie, _, _ = determinar_serie("Reporte", "Falla en tubería sector La Vega")
        assert serie == "OPS"

    def test_operativo_orden_trabajo(self):
        serie, _, _ = determinar_serie("Orden de trabajo", "Mantenimiento red distribución")
        assert serie == "OPS"

    def test_correspondencia_oficio(self):
        serie, subserie, _ = determinar_serie("Oficio", "Oficio remisorio a CAR")
        assert serie == "ADM"

    def test_sin_match_retorna_otr(self):
        serie, _, conf = determinar_serie("XYZ", "contenido genérico sin palabras clave")
        assert serie == "OTR"
        assert conf == "DEFAULT"


# ── clasificar_documento ─────────────────────────────────────────────────────

class TestClasificarDocumento:
    def test_retorna_dataclass(self):
        clf = clasificar_documento("Contrato", "Contrato de prestación de servicios")
        assert isinstance(clf, ClasificacionDocumental)
        assert clf.serie_codigo == "LEG"

    def test_fallback_por_area_gf(self):
        clf = clasificar_documento("Documento", "texto sin palabras clave", area="GF")
        assert clf.serie_codigo == "FIN"
        assert clf.confianza == "AREA"

    def test_fallback_por_area_gl(self):
        clf = clasificar_documento("Documento", "texto genérico", area="GL")
        assert clf.serie_codigo == "LEG"
        assert clf.confianza == "AREA"

    def test_regla_tiene_prioridad_sobre_area(self):
        clf = clasificar_documento("Petición", "Queja ciudadana", area="GF")
        assert clf.serie_codigo == "PQRS"
        assert clf.confianza == "REGLA"

    def test_to_dict_tiene_campos_requeridos(self):
        d = clasificar_documento("Acta", "Acta de asamblea 2026").to_dict()
        for campo in ["serie_codigo", "serie_nombre", "subserie", "retencion_gestion",
                      "retencion_central", "disposicion_final", "nivel_acceso", "confianza"]:
            assert campo in d, f"Campo faltante: {campo}"

    def test_pqrs_disposicion_eliminacion(self):
        clf = clasificar_documento("Queja", "Queja por presión baja")
        assert clf.disposicion_final == "eliminacion"

    def test_gobierno_retencion_larga(self):
        clf = clasificar_documento("Resolución", "Resolución de junta directiva")
        assert clf.retencion_central >= 10

    def test_legal_nivel_confidencial(self):
        clf = clasificar_documento("Contrato", "Contrato obra civil")
        assert clf.nivel_acceso == "Confidencial"

    def test_proyecto_nivel_publico(self):
        clf = clasificar_documento("Proyecto", "Proyecto de infraestructura vial")
        assert clf.nivel_acceso == "Publico"

    def test_sin_match_sin_area_retorna_otr(self):
        clf = clasificar_documento("", "")
        assert clf.serie_codigo == "OTR"
        assert clf.confianza == "DEFAULT"


# ── determinar_retencion ─────────────────────────────────────────────────────

class TestDeterminarRetencion:
    def test_fin_retencion_central_7(self):
        ret = determinar_retencion("FIN")
        assert ret["retencion_central"] >= 7

    def test_leg_retencion_central_15(self):
        ret = determinar_retencion("LEG")
        assert ret["retencion_central"] >= 15

    def test_pqrs_retencion_gestion_1(self):
        ret = determinar_retencion("PQRS")
        assert ret["retencion_gestion"] <= 2

    def test_serie_desconocida_retorna_default(self):
        ret = determinar_retencion("XYZ_NO_EXISTE")
        assert "retencion_gestion" in ret
        assert "disposicion_final" in ret


# ── determinar_nivel_acceso ──────────────────────────────────────────────────

class TestNivelAcceso:
    def test_fin_confidencial(self):
        assert determinar_nivel_acceso("FIN") == "Confidencial"

    def test_pry_publico(self):
        assert determinar_nivel_acceso("PRY") == "Publico"

    def test_tipo_con_contrasena_fuerza_confidencial(self):
        assert determinar_nivel_acceso("ADM", "contraseña SMTP") == "Confidencial"

    def test_otr_restringido(self):
        assert determinar_nivel_acceso("OTR") == "Restringido"
