"""
database/migrations/020_proyectos_periodo_flexible.py
Agrega tipo_periodo y cantidad_periodo a proyectos para soportar duraciones
trimestrales, semestrales, anuales y multianuales. (#50)
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
        existing = [r[1] for r in conn.execute("PRAGMA table_info(proyectos)").fetchall()]
        nuevos = {
            "tipo_periodo":     "TEXT DEFAULT 'ANIOS'",
            "cantidad_periodo": "INTEGER DEFAULT 1",
            "duracion_meses":   "INTEGER",
        }
        for col, tipo in nuevos.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE proyectos ADD COLUMN {col} {tipo}")
                print(f"✅ Migración 020: columna '{col}' agregada a proyectos.")
        # Calcular duracion_meses para proyectos existentes con fecha_inicio y fecha_limite
        conn.execute("""
            UPDATE proyectos
            SET duracion_meses = CAST(
                (julianday(fecha_limite) - julianday(fecha_inicio)) / 30.44 AS INTEGER
            )
            WHERE fecha_inicio IS NOT NULL
              AND fecha_limite IS NOT NULL
              AND duracion_meses IS NULL
        """)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        _log.error("migrar_020: %s", e, exc_info=True)
        print(f"❌ Error migración 020: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import sys, logging
    logging.basicConfig(level=logging.INFO)
    sys.exit(0 if migrar(sys.argv[1] if len(sys.argv) > 1 else None) else 1)
