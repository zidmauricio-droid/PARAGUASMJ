"""
database/migrations/017_pqrs_sspd_campos.py
Agrega campos SSPD a la tabla pqrs: tipo_solicitante, dane_municipio, grupo_causal.
Idempotente.
"""
import sqlite3, os, logging

_log = logging.getLogger("sigca.migrations")


def migrar(db_path: str = None) -> bool:
    if db_path is None:
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "paraguasmj.db"
        )
    if not os.path.exists(db_path):
        return False
    conn = sqlite3.connect(db_path)
    try:
        existing = [r[1] for r in conn.execute("PRAGMA table_info(pqrs)").fetchall()]
        nuevos = {
            "tipo_solicitante": "TEXT DEFAULT 'suscriptor'",
            "dane_municipio":   "TEXT DEFAULT '251750000'",
            "grupo_causal":     "TEXT DEFAULT ''",
        }
        for col, tipo in nuevos.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE pqrs ADD COLUMN {col} {tipo}")
                print(f"✅ Migración 017: columna '{col}' agregada a pqrs.")
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        _log.error("migrar_017: %s", e, exc_info=True)
        print(f"❌ Error migración 017: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import sys, logging
    logging.basicConfig(level=logging.INFO)
    sys.exit(0 if migrar(sys.argv[1] if len(sys.argv) > 1 else None) else 1)
