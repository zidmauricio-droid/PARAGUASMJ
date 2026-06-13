"""
028_puntos_concertacion.py — GA-06 Puntos de Concertación (cuenca hidrográfica).
Idempotente.
"""
import sqlite3


def migrar(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    tablas = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    if "ga_puntos_concertacion" not in tablas:
        conn.execute("""
            CREATE TABLE ga_puntos_concertacion (
                pk_punto_id          INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo               TEXT NOT NULL UNIQUE,
                nombre               TEXT NOT NULL,
                descripcion          TEXT,
                coordenada_lat       REAL,
                coordenada_lon       REAL,
                estado               TEXT DEFAULT 'ACTIVO'
                    CHECK(estado IN ('ACTIVO','SUSPENDIDO','VENCIDO','CERTIFICADO')),
                fecha_certificacion  TEXT,
                fecha_vencimiento    TEXT,
                entidad_certificadora TEXT,
                observaciones        TEXT,
                activo               INTEGER DEFAULT 1,
                fecha_creacion       TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_ga_conc_estado ON ga_puntos_concertacion(estado)")
        conn.execute("CREATE INDEX idx_ga_conc_activo ON ga_puntos_concertacion(activo)")

    if "ga_nivel_quebrada" not in tablas:
        conn.execute("""
            CREATE TABLE ga_nivel_quebrada (
                pk_nivel_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_punto_id    INTEGER,
                fecha          TEXT NOT NULL,
                nivel_cm       INTEGER NOT NULL,
                observaciones  TEXT,
                usuario        TEXT,
                fecha_registro TEXT DEFAULT (datetime('now')),
                UNIQUE(fk_punto_id, fecha)
            )
        """)
        conn.execute("CREATE INDEX idx_ga_nivel_fecha ON ga_nivel_quebrada(fecha)")

    conn.commit()
    conn.close()
