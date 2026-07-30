"""
027_ordenes_trabajo_rc6.py — GA-07 Órdenes de Trabajo RC6: materiales e imágenes.
Idempotente.
"""
import sqlite3


def migrar(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    cols_ot = {r[1] for r in conn.execute("PRAGMA table_info(ordenes_trabajo)").fetchall()}

    # Columnas nuevas en tabla base ordenes_trabajo
    for col, defn in [
        ("fk_suscriptor_id", "INTEGER"),
        ("fk_punto_gis_id",  "INTEGER"),
        ("prioridad",        "TEXT DEFAULT 'NORMAL'"),
        ("costo_estimado",   "REAL DEFAULT 0"),
        ("costo_real",       "REAL DEFAULT 0"),
    ]:
        if col not in cols_ot:
            try:
                conn.execute(f"ALTER TABLE ordenes_trabajo ADD COLUMN {col} {defn}")
            except Exception:
                pass

    tablas = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    if "ga_ot_materiales" not in tablas:
        conn.execute("""
            CREATE TABLE ga_ot_materiales (
                pk_mat_id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_ot_id           INTEGER NOT NULL,
                fk_item_id         INTEGER,
                descripcion        TEXT NOT NULL,
                cantidad           REAL NOT NULL,
                unidad             TEXT DEFAULT 'und',
                costo_unitario     REAL DEFAULT 0,
                fecha_uso          TEXT,
                observaciones      TEXT
            )
        """)
        conn.execute("CREATE INDEX idx_ga_ot_mat_ot ON ga_ot_materiales(fk_ot_id)")

    if "ga_ot_imagenes" not in tablas:
        conn.execute("""
            CREATE TABLE ga_ot_imagenes (
                pk_img_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_ot_id       INTEGER NOT NULL,
                ruta_archivo   TEXT NOT NULL,
                descripcion    TEXT,
                fecha_captura  TEXT DEFAULT (date('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_ga_ot_img_ot ON ga_ot_imagenes(fk_ot_id)")

    conn.commit()
    conn.close()
