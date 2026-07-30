"""
database/migrations/034_unificar_nivel_quebrada.py
RC6.2 — Eliminar tabla duplicada niveles_quebrada.
Migrar datos existentes a ga_nivel_quebrada.
Poblar escala inicial para fuente FH-001 (0..200 cm cada 20 cm).
Idempotente.
"""
import sqlite3, os, logging

_log = logging.getLogger("sigca.migrations")

_ESCALA_DEFAULT = [0, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200]


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

        # ── Migrar datos de niveles_quebrada → ga_nivel_quebrada ──────────
        if "niveles_quebrada" in tablas and "ga_nivel_quebrada" in tablas:
            cols_old = {r[1] for r in conn.execute("PRAGMA table_info(niveles_quebrada)").fetchall()}
            cols_new = {r[1] for r in conn.execute("PRAGMA table_info(ga_nivel_quebrada)").fetchall()}
            if "nivel_cm" in cols_old and "nivel_cm" in cols_new:
                conn.execute("""
                    INSERT OR IGNORE INTO ga_nivel_quebrada (anio, mes, fecha_lectura, nivel_cm, rango_estandar)
                    SELECT strftime('%Y', fecha) as anio,
                           CAST(strftime('%m', fecha) AS INTEGER) as mes,
                           fecha, nivel_cm,
                           CASE WHEN nivel_cm % 20 = 0 THEN CAST(nivel_cm AS INTEGER) ELSE NULL END
                    FROM niveles_quebrada
                    WHERE fecha IS NOT NULL AND nivel_cm IS NOT NULL
                """)
                _log.info("034: datos migrados de niveles_quebrada a ga_nivel_quebrada")

        # ── Poblar escala inicial en ga_escala_medicion ───────────────────
        if "ga_escala_medicion" in tablas and "ga_fuentes_hidricas" in tablas:
            fuente = conn.execute(
                "SELECT pk_fuente_id FROM ga_fuentes_hidricas WHERE codigo='FH-001' LIMIT 1"
            ).fetchone()
            if fuente:
                fid = fuente[0]
                ya_tiene = conn.execute(
                    "SELECT COUNT(*) FROM ga_escala_medicion WHERE fk_fuente_id=?", (fid,)
                ).fetchone()[0]
                if not ya_tiene:
                    for orden, val in enumerate(_ESCALA_DEFAULT):
                        conn.execute(
                            "INSERT OR IGNORE INTO ga_escala_medicion (fk_fuente_id, valor, orden) VALUES (?,?,?)",
                            (fid, val, orden)
                        )
                    # Marcar fuente como controlada
                    conn.execute(
                        "UPDATE ga_fuentes_hidricas SET escala_tipo='controlada' WHERE pk_fuente_id=?",
                        (fid,)
                    )
                    _log.info("034: escala 0-200cm (cada 20cm) poblada para FH-001")

        conn.commit()
        _log.info("Migración 034: unificación nivel quebrada completada.")
        return True
    except Exception as e:
        conn.rollback()
        _log.error("migrar_034: %s", e, exc_info=True)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    sys.exit(0 if migrar(sys.argv[1] if len(sys.argv) > 1 else None) else 1)
