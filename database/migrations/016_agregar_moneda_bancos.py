"""
database/migrations/016_agregar_moneda_bancos.py
Agrega columna 'moneda' a la tabla bancos si no existe.
Idempotente: puede ejecutarse múltiples veces sin error.
"""
import sqlite3
import os
import logging

_log = logging.getLogger("sigca.migrations")


def migrar(db_path: str = None) -> bool:
    if db_path is None:
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "paraguasmj.db"
        )

    if not os.path.exists(db_path):
        _log.warning("migrar_016: BD no encontrada en %s", db_path)
        return False

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        columnas = [r["name"] for r in conn.execute("PRAGMA table_info(bancos)").fetchall()]

        if "moneda" not in columnas:
            _log.info("migrar_016: agregando columna 'moneda' a bancos")
            conn.execute("ALTER TABLE bancos ADD COLUMN moneda TEXT NOT NULL DEFAULT 'COP'")
            conn.execute("UPDATE bancos SET moneda='COP' WHERE moneda IS NULL OR moneda=''")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_bancos_moneda ON bancos(moneda)"
            )
            conn.commit()
            print("✅ Migración 016: columna 'moneda' agregada a bancos.")
        else:
            print("✅ Migración 016: columna 'moneda' ya existe, sin cambios.")

        return True
    except Exception as e:
        conn.rollback()
        _log.error("migrar_016: %s", e, exc_info=True)
        print(f"❌ Error en migración 016: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    path = sys.argv[1] if len(sys.argv) > 1 else None
    ok = migrar(path)
    sys.exit(0 if ok else 1)
