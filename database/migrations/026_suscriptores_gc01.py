"""
026_suscriptores_gc01.py — GC-01 Gestión Comercial: Suscriptores y Conexiones.
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

    if "gc_suscriptores" not in tablas:
        conn.execute("""
            CREATE TABLE gc_suscriptores (
                pk_suscriptor_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_contacto_id     INTEGER,
                codigo_suscriptor  TEXT NOT NULL UNIQUE,
                numero_medidor     TEXT,
                fecha_conexion     TEXT,
                tipo_suscriptor    TEXT DEFAULT 'RESIDENCIAL'
                    CHECK(tipo_suscriptor IN ('RESIDENCIAL','COMERCIAL','INSTITUCIONAL','INDUSTRIAL')),
                estado             TEXT DEFAULT 'ACTIVO'
                    CHECK(estado IN ('ACTIVO','SUSPENDIDO','CORTADO','INACTIVO')),
                estrato            INTEGER DEFAULT 1,
                aforo_m3           REAL DEFAULT 0,
                fk_zona_id         INTEGER,
                coordenada_lat     REAL,
                coordenada_lon     REAL,
                saldo_cartera      REAL DEFAULT 0,
                observaciones      TEXT,
                fecha_creacion     TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_gc_sus_estado ON gc_suscriptores(estado)")
        conn.execute("CREATE INDEX idx_gc_sus_zona ON gc_suscriptores(fk_zona_id)")
        conn.execute("CREATE INDEX idx_gc_sus_codigo ON gc_suscriptores(codigo_suscriptor)")

    if "gc_conexiones" not in tablas:
        conn.execute("""
            CREATE TABLE gc_conexiones (
                pk_conexion_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_suscriptor_id   INTEGER,
                tipo               TEXT NOT NULL
                    CHECK(tipo IN ('NUEVA','RECONEXION','CORTE','AMPLIACION')),
                fecha_solicitud    TEXT NOT NULL,
                fecha_ejecucion    TEXT,
                estado             TEXT DEFAULT 'PENDIENTE'
                    CHECK(estado IN ('PENDIENTE','APROBADA','EJECUTADA','RECHAZADA')),
                valor_cobrado      REAL DEFAULT 0,
                tecnico_asignado   TEXT,
                fk_documento_id    INTEGER,
                observaciones      TEXT,
                usuario            TEXT,
                fecha_creacion     TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_gc_con_suscriptor ON gc_conexiones(fk_suscriptor_id)")
        conn.execute("CREATE INDEX idx_gc_con_estado ON gc_conexiones(estado)")

    # Tabla para causales PQRS parametrizables (Nivel 3 — aprobado RC6)
    if "gc_pqrs_causales" not in tablas:
        conn.execute("""
            CREATE TABLE gc_pqrs_causales (
                pk_causal_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo         TEXT NOT NULL UNIQUE,
                nombre         TEXT NOT NULL,
                servicio       TEXT DEFAULT 'ACUEDUCTO'
                    CHECK(servicio IN ('ACUEDUCTO','ALCANTARILLADO','AMBOS')),
                sla_dias       INTEGER DEFAULT 15,
                activo         INTEGER DEFAULT 1,
                orden          INTEGER DEFAULT 0
            )
        """)
        # Causales base — parametrizables y editables por el administrador
        causales = [
            ("C-001", "Calidad del agua suministrada",     "ACUEDUCTO",      15),
            ("C-002", "Baja presión en el servicio",       "ACUEDUCTO",      15),
            ("C-003", "Intermitencia en el servicio",      "ACUEDUCTO",      10),
            ("C-004", "Fugas en redes internas",           "ACUEDUCTO",      15),
            ("C-005", "Daño en medidor",                   "ACUEDUCTO",      15),
            ("C-006", "Solicitud nueva conexión",          "ACUEDUCTO",      30),
            ("C-007", "Solicitud reconexión",              "ACUEDUCTO",       5),
            ("C-008", "Obstrucción de alcantarillado",     "ALCANTARILLADO",  5),
            ("C-009", "Desbordamiento de colector",        "ALCANTARILLADO",  3),
            ("C-010", "Solicitud nueva conexión alc.",     "ALCANTARILLADO", 30),
            ("C-011", "Atención al usuario",               "AMBOS",          15),
            ("C-012", "Información tarifaria",             "AMBOS",          15),
            ("C-013", "Acuerdo de pago",                   "AMBOS",          10),
        ]
        for c in causales:
            conn.execute(
                "INSERT OR IGNORE INTO gc_pqrs_causales (codigo,nombre,servicio,sla_dias) VALUES (?,?,?,?)",
                c
            )

    conn.commit()
    conn.close()
