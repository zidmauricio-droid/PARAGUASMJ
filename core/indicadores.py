"""core/indicadores.py — Calculo de indicadores CRA/SSPD."""
import logging
from core.database_manager import get_db

logger = logging.getLogger("asuacap.indicadores")


def calcular_ianc(produccion_m3: float, facturado_m3: float) -> float | None:
    """IANC = (Producido - Facturado) / Producido * 100"""
    if produccion_m3 and produccion_m3 > 0:
        return round(((produccion_m3 - facturado_m3) / produccion_m3) * 100, 2)
    return None


def actualizar_indicadores_mensuales(anio: int, mes: int) -> None:
    """Recalcula y guarda indicadores del mes en indicadores_mensuales."""
    conn = get_db()
    try:
        mes_str = f"{mes:02d}"
        prod = conn.execute("""
            SELECT COALESCE(SUM(produccion_diaria),0) as total
            FROM lecturas_macromedicion
            WHERE strftime('%Y',fecha)=? AND strftime('%m',fecha)=?
        """, (str(anio), mes_str)).fetchone()["total"]

        bh = conn.execute("""
            SELECT COALESCE(facturado_m3,0) as fac, COALESCE(perdidas_m3,0) as perd
            FROM balance_hidrico WHERE anio=? AND mes=?
        """, (anio, mes)).fetchone()

        fac = bh["fac"] if bh else 0
        perd = prod - fac

        ianc = calcular_ianc(prod, fac)

        # Cobertura micromedicion
        total_susc = conn.execute(
            "SELECT COUNT(*) as t FROM contactos WHERE tipo_contacto='Suscriptor' AND activo_desactivo='ACTIVO'"
        ).fetchone()["t"]
        con_med = conn.execute(
            "SELECT COUNT(*) as t FROM contactos WHERE tipo_contacto='Suscriptor' AND micromedidor_si_no='SI' AND activo_desactivo='ACTIVO'"
        ).fetchone()["t"]
        irac = round((con_med / total_susc * 100) if total_susc > 0 else 0, 2)

        conn.execute("""
            INSERT INTO indicadores_mensuales(anio,mes,produccion_m3,facturado_m3,perdidas_m3,ianc,irac)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(anio,mes) DO UPDATE SET
                produccion_m3=excluded.produccion_m3,
                facturado_m3=excluded.facturado_m3,
                perdidas_m3=excluded.perdidas_m3,
                ianc=excluded.ianc,
                irac=excluded.irac
        """, (anio, mes, round(prod,2), round(fac,2), round(perd,2), ianc, irac))
        conn.commit()
        logger.info(f"Indicadores actualizados: {anio}-{mes} IANC={ianc}%")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error calculando indicadores: {e}")
    finally:
        conn.close()
