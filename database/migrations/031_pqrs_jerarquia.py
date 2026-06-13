"""
031_pqrs_jerarquia.py — PQRS 4-level hierarchy.
gc_servicios, gc_tipo_solicitante, gc_medios_recepcion.
fk_servicio_id added to gc_pqrs_causales.
Idempotent.
"""
import sqlite3


def migrar(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    tablas = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    if "gc_servicios" not in tablas:
        conn.execute("""
            CREATE TABLE gc_servicios (
                pk_servicio_id INTEGER PRIMARY KEY,
                codigo         TEXT NOT NULL UNIQUE,
                nombre         TEXT NOT NULL,
                activo         INTEGER DEFAULT 1
            )
        """)
        conn.executemany(
            "INSERT OR IGNORE INTO gc_servicios VALUES (?,?,?,1)",
            [(1, "ACUEDUCTO", "Acueducto"),
             (2, "ALCANTARILLADO", "Alcantarillado")]
        )

    if "gc_tipo_solicitante" not in tablas:
        conn.execute("""
            CREATE TABLE gc_tipo_solicitante (
                pk_tipo_id  INTEGER PRIMARY KEY,
                codigo      TEXT NOT NULL UNIQUE,
                nombre      TEXT NOT NULL,
                descripcion TEXT,
                activo      INTEGER DEFAULT 1
            )
        """)
        conn.executemany(
            "INSERT OR IGNORE INTO gc_tipo_solicitante VALUES (?,?,?,?,1)",
            [(1, "SUSCRIPTOR", "Suscriptor",  "Usuario con contrato de servicio"),
             (2, "USUARIO",    "Usuario",     "Sin contrato — uso ocasional"),
             (3, "ENTIDAD",    "Entidad",     "Persona jurídica o entidad externa")]
        )

    if "gc_medios_recepcion" not in tablas:
        conn.execute("""
            CREATE TABLE gc_medios_recepcion (
                pk_medio_id INTEGER PRIMARY KEY,
                codigo      TEXT NOT NULL UNIQUE,
                nombre      TEXT NOT NULL,
                codigo_sui  TEXT,
                activo      INTEGER DEFAULT 1
            )
        """)
        conn.executemany(
            "INSERT OR IGNORE INTO gc_medios_recepcion VALUES (?,?,?,?,1)",
            [(1, "PRESENCIAL",  "Presencial / Ventanilla",   "01"),
             (2, "TELEFONO",    "Telefónico",                 "02"),
             (3, "WEB",         "Web / Formulario en línea",  "03"),
             (4, "CORREO",      "Correo electrónico",         "04"),
             (5, "WHATSAPP",    "WhatsApp",                   "99"),
             (6, "ESCRITO",     "Correspondencia escrita",    "08")]
        )

    # Add fk_servicio_id to gc_pqrs_causales (idempotent ALTER)
    if "gc_pqrs_causales" in tablas:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(gc_pqrs_causales)").fetchall()}
        if "fk_servicio_id" not in cols:
            conn.execute("ALTER TABLE gc_pqrs_causales ADD COLUMN fk_servicio_id INTEGER")
            conn.execute("UPDATE gc_pqrs_causales SET fk_servicio_id=1 WHERE servicio='ACUEDUCTO'")
            conn.execute("UPDATE gc_pqrs_causales SET fk_servicio_id=2 WHERE servicio='ALCANTARILLADO'")

    conn.commit()
    conn.close()
