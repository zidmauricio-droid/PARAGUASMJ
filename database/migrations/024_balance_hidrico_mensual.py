"""
database/migrations/024_balance_hidrico_mensual.py
RC6 GA-03 — Balance Hídrico con macromedidor mensual y nivel de quebrada.
Solo lecturas mensuales. Fuente principal: macromedidor.
Idempotente.
"""
import sqlite3, os, logging

_log = logging.getLogger("sigca.migrations")

_RANGOS_QUEBRADA = [0, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200]


def migrar(db_path: str = None) -> bool:
    if db_path is None:
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "paraguasmj.db"
        )
    if not os.path.exists(db_path):
        return False
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        # ── Lecturas macromedidor mensual ────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bh_macromedidor_mensual (
                pk_lectura_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                anio             INTEGER NOT NULL,
                mes              INTEGER NOT NULL CHECK(mes BETWEEN 1 AND 12),
                fecha_lectura    TEXT NOT NULL,
                lectura_inicial  REAL NOT NULL DEFAULT 0,
                lectura_final    REAL NOT NULL DEFAULT 0,
                volumen_producido REAL GENERATED ALWAYS AS
                    (ROUND(lectura_final - lectura_inicial, 2)) STORED,
                observaciones    TEXT DEFAULT '',
                responsable      TEXT DEFAULT '',
                fecha_registro   TEXT DEFAULT (datetime('now')),
                UNIQUE (anio, mes)
            )
        """)

        # ── Niveles de quebrada mensuales ────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bh_nivel_quebrada (
                pk_nivel_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                anio             INTEGER NOT NULL,
                mes              INTEGER NOT NULL CHECK(mes BETWEEN 1 AND 12),
                fecha_lectura    TEXT NOT NULL,
                nivel_cm         REAL NOT NULL,
                rango_estandar   INTEGER,
                observaciones    TEXT DEFAULT '',
                responsable      TEXT DEFAULT '',
                fecha_registro   TEXT DEFAULT (datetime('now')),
                UNIQUE (anio, mes)
            )
        """)

        # ── Resumen mensual de balance (calculado) ───────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bh_resumen_mensual (
                pk_resumen_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                anio             INTEGER NOT NULL,
                mes              INTEGER NOT NULL CHECK(mes BETWEEN 1 AND 12),
                volumen_producido_m3  REAL DEFAULT 0,
                volumen_facturado_m3  REAL DEFAULT 0,
                perdidas_m3           REAL DEFAULT 0,
                ianc_pct              REAL DEFAULT 0,
                suscriptores_activos  INTEGER DEFAULT 0,
                observaciones         TEXT DEFAULT '',
                fecha_calculo         TEXT DEFAULT (datetime('now')),
                UNIQUE (anio, mes)
            )
        """)

        # ── Índices ──────────────────────────────────────────────────────────
        for idx, target in [
            ("idx_bh_macro_anio_mes",   "bh_macromedidor_mensual(anio, mes)"),
            ("idx_bh_nivel_anio_mes",   "bh_nivel_quebrada(anio, mes)"),
            ("idx_bh_resumen_anio_mes", "bh_resumen_mensual(anio, mes)"),
        ]:
            try:
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {target}")
            except Exception as ei:
                _log.warning("024: índice %s omitido: %s", idx, ei)

        conn.commit()
        _log.info("Migración 024: balance hídrico mensual (macromedidor + nivel quebrada) creado.")
        return True
    except Exception as e:
        conn.rollback()
        _log.error("migrar_024: %s", e, exc_info=True)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    sys.exit(0 if migrar(sys.argv[1] if len(sys.argv) > 1 else None) else 1)
