"""
database/migrations/032_pqrs_rc6_campos.py
RC6.2 — PQRS: columnas FK para jerarquía RC6 (servicio/tipo_solicitante/medio/causal).
Elimina dependencia del código de los diccionarios SSPD estáticos para el flujo de registro.
Idempotente.
"""
import sqlite3, os, logging

_log = logging.getLogger("sigca.migrations")

_COLS = [
    ("fk_servicio_id",          "INTEGER REFERENCES gc_servicios(pk_servicio_id)"),
    ("fk_tipo_solicitante_id",  "INTEGER REFERENCES gc_tipo_solicitante(pk_tipo_id)"),
    ("fk_medio_id",             "INTEGER REFERENCES gc_medios_recepcion(pk_medio_id)"),
    ("fk_causal_id",            "INTEGER REFERENCES gc_pqrs_causales(pk_causal_id)"),
]


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
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "pqrs" not in tablas:
            _log.warning("032: tabla pqrs no existe — omitiendo")
            conn.close()
            return True

        cols_actuales = {r[1] for r in conn.execute("PRAGMA table_info(pqrs)").fetchall()}
        for col, definicion in _COLS:
            if col not in cols_actuales:
                conn.execute(f"ALTER TABLE pqrs ADD COLUMN {col} {definicion}")
                _log.info("032: columna pqrs.%s añadida", col)

        conn.commit()
        _log.info("Migración 032: columnas RC6 en tabla pqrs aplicadas.")
        return True
    except Exception as e:
        conn.rollback()
        _log.error("migrar_032: %s", e, exc_info=True)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    sys.exit(0 if migrar(sys.argv[1] if len(sys.argv) > 1 else None) else 1)
