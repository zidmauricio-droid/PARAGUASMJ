"""
database/migrations/033_ga03_fuentes_hidricas.py
RC6.2 — GA-03: Monitoreo genérico de fuentes hídricas.
Aplica para cualquier tipo de prestador: nacedero, río, quebrada, pozo, embalse, laguna.
La unidad y la escala de medición son configurables por cliente.
Idempotente.
"""
import sqlite3, os, logging

_log = logging.getLogger("sigca.migrations")

_DDL = [
    # Fuentes hídricas configurables por cliente
    """CREATE TABLE IF NOT EXISTS ga_fuentes_hidricas (
        pk_fuente_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo          TEXT NOT NULL,
        nombre          TEXT NOT NULL,
        tipo_fuente     TEXT NOT NULL DEFAULT 'Quebrada',
        descripcion     TEXT DEFAULT '',
        unidad_medicion TEXT NOT NULL DEFAULT 'cm',
        escala_tipo     TEXT NOT NULL DEFAULT 'libre'
                        CHECK(escala_tipo IN ('libre','controlada')),
        activo          INTEGER NOT NULL DEFAULT 1,
        fecha_registro  TEXT DEFAULT (datetime('now')),
        UNIQUE(codigo)
    )""",

    # Valores permitidos cuando escala_tipo='controlada'
    """CREATE TABLE IF NOT EXISTS ga_escala_medicion (
        pk_escala_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_fuente_id    INTEGER NOT NULL REFERENCES ga_fuentes_hidricas(pk_fuente_id),
        valor           REAL NOT NULL,
        descripcion     TEXT DEFAULT '',
        orden           INTEGER DEFAULT 0,
        UNIQUE(fk_fuente_id, valor)
    )""",

    # Mediciones individuales: cada lectura de campo
    """CREATE TABLE IF NOT EXISTS ga_mediciones_fuente (
        pk_medicion_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_fuente_id    INTEGER NOT NULL REFERENCES ga_fuentes_hidricas(pk_fuente_id),
        fecha           TEXT NOT NULL,
        hora            TEXT DEFAULT '',
        punto_medicion  TEXT DEFAULT 'Principal',
        valor_observado REAL NOT NULL,
        unidad          TEXT NOT NULL,
        nivel_alerta    TEXT DEFAULT 'normal'
                        CHECK(nivel_alerta IN ('normal','naranja','rojo')),
        responsable     TEXT DEFAULT '',
        observaciones   TEXT DEFAULT '',
        fecha_registro  TEXT DEFAULT (datetime('now'))
    )""",
]

_INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_ga_fuentes_activo ON ga_fuentes_hidricas(activo)",
    "CREATE INDEX IF NOT EXISTS idx_ga_mediciones_fuente_fecha ON ga_mediciones_fuente(fk_fuente_id, fecha)",
    "CREATE INDEX IF NOT EXISTS idx_ga_escala_fuente ON ga_escala_medicion(fk_fuente_id, orden)",
]

# Fuente de ejemplo genérica (no específica de cliente; se puede editar o eliminar)
_SEED = """
    INSERT OR IGNORE INTO ga_fuentes_hidricas
        (codigo, nombre, tipo_fuente, unidad_medicion, escala_tipo)
    VALUES
        ('FH-001', 'Fuente principal', 'Quebrada', 'cm', 'libre')
"""


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
        for ddl in _DDL:
            conn.execute(ddl)
        for idx in _INDICES:
            try:
                conn.execute(idx)
            except Exception as ei:
                _log.warning("033: índice omitido: %s", ei)
        conn.execute(_SEED)
        conn.commit()
        _log.info("Migración 033: GA-03 fuentes hídricas genéricas creadas.")
        return True
    except Exception as e:
        conn.rollback()
        _log.error("migrar_033: %s", e, exc_info=True)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    sys.exit(0 if migrar(sys.argv[1] if len(sys.argv) > 1 else None) else 1)
