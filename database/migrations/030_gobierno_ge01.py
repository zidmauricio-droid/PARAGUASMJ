"""
030_gobierno_ge01.py — GE-01 Gobierno Corporativo: Actas y Resoluciones.
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

    if "ge_actas" not in tablas:
        conn.execute("""
            CREATE TABLE ge_actas (
                pk_acta_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo             TEXT NOT NULL
                    CHECK(tipo IN ('ASAMBLEA','JUNTA','COMITE','EXTRAORDINARIA')),
                numero_acta      TEXT NOT NULL,
                anio             INTEGER NOT NULL,
                fecha_reunion    TEXT NOT NULL,
                lugar            TEXT,
                quorum_requerido INTEGER,
                quorum_presente  INTEGER,
                orden_del_dia    TEXT,
                decisiones       TEXT,
                estado           TEXT DEFAULT 'BORRADOR'
                    CHECK(estado IN ('BORRADOR','APROBADA','ARCHIVADA')),
                fk_documento_id  INTEGER,
                usuario          TEXT,
                fecha_creacion   TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_ge_actas_tipo ON ge_actas(tipo)")
        conn.execute("CREATE INDEX idx_ge_actas_anio ON ge_actas(anio)")

    if "ge_resoluciones" not in tablas:
        conn.execute("""
            CREATE TABLE ge_resoluciones (
                pk_res_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                numero           TEXT NOT NULL,
                anio             INTEGER NOT NULL,
                fecha_expedicion TEXT NOT NULL,
                asunto           TEXT NOT NULL,
                descripcion      TEXT,
                estado           TEXT DEFAULT 'VIGENTE'
                    CHECK(estado IN ('VIGENTE','DEROGADA','SUSPENDIDA')),
                fk_documento_id  INTEGER,
                usuario          TEXT,
                fecha_creacion   TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_ge_res_estado ON ge_resoluciones(estado)")
        conn.execute("CREATE INDEX idx_ge_res_anio   ON ge_resoluciones(anio)")

    conn.commit()
    conn.close()
