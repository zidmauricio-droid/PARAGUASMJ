"""
core/indicadores_ius.py
Indicadores CRA / SSPD / CAR - normativa colombiana.
Res. CRA 906/2019 (IUS), Ley 373/1997 (PUEAA).
Fuente: PROGRAMA_1.doc - todos los calculos documentados.
"""
import logging
from core.database_manager import get_db

logger = logging.getLogger("asuacap.ius")


def ianc(producido, facturado):
    """IANC = (Producido - Facturado) / Producido * 100"""
    if producido and producido > 0:
        return round((producido - facturado) / producido * 100, 2)
    return None

def ipaa(captado, llegada_tanque):
    """IPAA = (Captado - Llegada tanque) / Captado * 100"""
    if captado and captado > 0:
        return round((captado - llegada_tanque) / captado * 100, 2)
    return None

def ima(macro_func, total_tramos):
    """IMA = (Macromedidores funcionando / Tramos) * 100"""
    if total_tramos and total_tramos > 0:
        return round((macro_func / total_tramos) * 100, 2)
    return None

def eet(kwh, vol_m3):
    """EET = kWh / m3 producido"""
    if vol_m3 and vol_m3 > 0:
        return round(kwh / vol_m3, 4)
    return None

def poacg(empleados, suscriptores):
    """POACg = (Empleados / Suscriptores) * 1000"""
    if suscriptores and suscriptores > 0:
        return round((empleados / suscriptores) * 1000, 4)
    return None

def continuidad(horas_dia):
    return round(horas_dia / 24, 4) if horas_dia is not None else None

def cobertura(con_servicio, total_viviendas):
    if total_viviendas and total_viviendas > 0:
        return round(con_servicio / total_viviendas, 4)
    return None

def irac_micromedicion(con_medidor, total_susc):
    if total_susc and total_susc > 0:
        return round(con_medidor / total_susc, 4)
    return None

def fallas_por_km(num_fallas, longitud_km):
    if longitud_km and longitud_km > 0:
        return round(num_fallas / longitud_km, 4)
    return None

def balance_componente(entrada_m3, salida_m3):
    perdida = entrada_m3 - salida_m3
    pct = round(perdida / entrada_m3 * 100, 2) if entrada_m3 > 0 else 0
    return {
        "entrada_m3": round(entrada_m3, 2),
        "salida_m3": round(salida_m3, 2),
        "perdida_m3": round(perdida, 2),
        "porcentaje_perdida": pct
    }


def calcular_ius_anual(anio: int) -> dict:
    """
    Calcula todos los indicadores del IUS para un año completo.
    Lee de las tablas del sistema PARAGUASMJ.
    Retorna dict con todos los indices para FC15 (SSPD).
    """
    conn = get_db()
    resultado = {"anio": anio, "indicadores": {}, "errores": []}

    try:
        # Balance hidrico anual
        bh = conn.execute("""
            SELECT COALESCE(SUM(produccion_m3),0) as prod,
                   COALESCE(SUM(facturado_m3),0) as fac
            FROM balance_hidrico WHERE anio=?
        """, (anio,)).fetchone()
        prod = float(bh["prod"]); fac = float(bh["fac"])
        resultado["indicadores"]["produccion_m3_anual"] = round(prod, 2)
        resultado["indicadores"]["facturado_m3_anual"]  = round(fac, 2)
        resultado["indicadores"]["perdidas_m3_anual"]   = round(prod - fac, 2)
        resultado["indicadores"]["IANC"] = ianc(prod, fac)

        # Suscriptores
        total_susc = conn.execute(
            "SELECT COUNT(*) as c FROM contactos WHERE tipo_contacto='Suscriptor' AND activo_desactivo='ACTIVO'"
        ).fetchone()["c"]
        con_med = conn.execute(
            "SELECT COUNT(*) as c FROM contactos WHERE tipo_contacto='Suscriptor' AND micromedidor_si_no='SI' AND activo_desactivo='ACTIVO'"
        ).fetchone()["c"]
        resultado["indicadores"]["total_suscriptores"] = total_susc
        resultado["indicadores"]["con_micromedidor"]   = con_med
        resultado["indicadores"]["IRAC"] = irac_micromedicion(con_med, total_susc)

        # Fallas en red
        fallas_n = conn.execute(
            "SELECT COUNT(*) as c FROM gis_reportes_fallas WHERE strftime('%Y',fecha_registro)=?",
            (str(anio),)
        ).fetchone()["c"]
        resultado["indicadores"]["fallas_anio"] = fallas_n

        # Configuracion operativa
        cfg = {}
        rows = conn.execute("""
            SELECT clave, valor FROM configuracion
            WHERE clave IN ('longitud_red_km','horas_servicio_dia','empleados_operativos',
                            'total_viviendas','kwh_anuales','macromedidores_func','total_tramos',
                            'irca_ultimo')
        """).fetchall()
        for r in rows:
            cfg[r["clave"]] = r["valor"]

        long_red   = float(cfg.get("longitud_red_km") or 12.5)
        horas_srv  = float(cfg.get("horas_servicio_dia") or 18)
        empleados  = int(cfg.get("empleados_operativos") or 3)
        viviendas  = int(cfg.get("total_viviendas") or 260)
        kwh_anu    = float(cfg.get("kwh_anuales") or 0)
        macro_func = int(cfg.get("macromedidores_func") or 1)
        tramos     = int(cfg.get("total_tramos") or 3)
        irca       = float(cfg.get("irca_ultimo") or 5)

        resultado["indicadores"]["fallas_por_km"] = fallas_por_km(fallas_n, long_red)
        resultado["indicadores"]["continuidad"]   = continuidad(horas_srv)
        resultado["indicadores"]["cobertura"]     = cobertura(total_susc, viviendas)
        resultado["indicadores"]["EET"]           = eet(kwh_anu, prod) if kwh_anu > 0 else None
        resultado["indicadores"]["IMA"]           = ima(macro_func, tramos)
        resultado["indicadores"]["POACg"]         = poacg(empleados, total_susc)
        resultado["indicadores"]["IRCA"]          = irca

        # IUS compuesto
        resultado["indicadores"]["IUS"] = calcular_ius_compuesto(resultado["indicadores"])

    except Exception as e:
        logger.error(f"Error IUS {anio}: {e}")
        resultado["errores"].append(str(e))
    finally:
        conn.close()

    return resultado


def calcular_ius_compuesto(ind: dict):
    """
    IUS ponderado segun CRA Res 906/2019 (adaptado acueductos rurales).
    Escala 0-100 donde 100 es optimo.
    """
    try:
        c         = ind.get("continuidad") or 0
        cv        = ind.get("cobertura")   or 0
        ir        = ind.get("IRAC")        or 0
        ianc_val  = ind.get("IANC")        or 50
        ianc_inv  = max(0, 1 - (ianc_val / 100))
        eet_val   = ind.get("EET")         or 0
        eet_norm  = max(0, 1 - min(eet_val, 1))
        poac_val  = ind.get("POACg")       or 0
        poac_norm = min(poac_val / 10, 1)
        irca_val  = ind.get("IRCA")        or 5
        irca_norm = max(0, 1 - (irca_val / 100))

        ius = (c          * 0.20 +
               cv         * 0.20 +
               ir         * 0.15 +
               irca_norm  * 0.10 +
               eet_norm   * 0.15 +
               poac_norm  * 0.10 +
               ianc_inv   * 0.10)
        return round(ius * 100, 2)
    except Exception:
        return None
