"""
database/migrations/022_rc6_areas_estructura.py
RC6 — Nueva estructura de áreas institucionales GE/GC/GF/GA/GL
Crea: areas_institucionales, subáreas, nuevo catálogo de causales PQRS (100-700),
tabla suscriptores_registro, tabla calidad_agua_muestras, tabla inventario_items.
Idempotente.
"""
import sqlite3, os, logging

_log = logging.getLogger("sigca.migrations")

_AREAS = [
    ("GE", "Gestión Estratégica",       1),
    ("GC", "Gestión Comercial",         2),
    ("GF", "Gestión Financiera",        3),
    ("GA", "Gestión Ambiental y Operativa", 4),
    ("GL", "Gestión Laboral",           5),
]

_SUBAREAS = [
    ("GE-01", "GE", "Gobierno Corporativo",      1),
    ("GE-02", "GE", "Planeación",               2),
    ("GE-03", "GE", "Control Interno",           3),
    ("GE-04", "GE", "Jurídica",                  4),
    ("GE-05", "GE", "Gestión Documental",        5),
    ("GC-01", "GC", "Suscriptores",              1),
    ("GC-02", "GC", "PQRS",                      2),
    ("GC-03", "GC", "Cartera",                   3),
    ("GC-04", "GC", "Conexiones",                4),
    ("GC-05", "GC", "Fraudes",                   5),
    ("GF-01", "GF", "Presupuesto",               1),
    ("GF-02", "GF", "Tesorería",                 2),
    ("GF-03", "GF", "Contabilidad",              3),
    ("GF-04", "GF", "Contratación",              4),
    ("GF-05", "GF", "Inventarios",               5),
    ("GF-06", "GF", "Caja",                      6),
    ("GA-01", "GA", "Infraestructura Operativa", 1),
    ("GA-02", "GA", "Calidad de Agua",           2),
    ("GA-03", "GA", "Balance Hídrico",           3),
    ("GA-04", "GA", "Infraestructura Técnica y Planos", 4),
    ("GA-05", "GA", "Mantenimiento",             5),
    ("GA-06", "GA", "Cuenca Hidrográfica",       6),
    ("GA-07", "GA", "Puntos de Concertación",    7),
    ("GA-08", "GA", "Nivel de Quebrada",         8),
    ("GA-09", "GA", "Resultados de Laboratorio", 9),
    ("GL-01", "GL", "Personal",                  1),
    ("GL-02", "GL", "Selección",                 2),
    ("GL-03", "GL", "Evaluación",                3),
    ("GL-04", "GL", "Capacitación",              4),
    ("GL-05", "GL", "SST",                       5),
]

# Nuevo catálogo de causales PQRS (series 100-700)
_CAUSALES_RC6 = [
    # serie, codigo, nombre, sla_dias, servicio
    ("100", "101", "Agua con color anormal",            5, "ACU"),
    ("100", "102", "Agua con olor anormal",             5, "ACU"),
    ("100", "103", "Agua con sabor anormal",            5, "ACU"),
    ("100", "104", "Agua turbia",                       3, "ACU"),
    ("100", "105", "Presencia de partículas",           3, "ACU"),
    ("100", "106", "Resultado laboratorio no conforme", 5, "ACU"),
    ("100", "107", "Posible contaminación",             2, "ACU"),
    ("100", "108", "Baja desinfección",                 3, "ACU"),
    ("200", "201", "Suspensión sin aviso",              5, "ACU"),
    ("200", "202", "Suspensión injustificada",          5, "ACU"),
    ("200", "203", "Negativa de suspensión solicitada", 5, "ACU"),
    ("200", "204", "Suspensión errónea",                5, "ACU"),
    ("200", "205", "Corte por error administrativo",    3, "ACU"),
    ("300", "301", "Retraso reconexión",                3, "ACU"),
    ("300", "302", "Cobro reconexión discutido",        10, "ACU"),
    ("300", "303", "Reconexión incompleta",             3, "ACU"),
    ("300", "304", "Reconexión no realizada",           2, "ACU"),
    ("400", "401", "Fuga red principal",                2, "ACU"),
    ("400", "402", "Fuga acometida",                    3, "ACU"),
    ("400", "403", "Daño tubería",                      3, "ACU"),
    ("400", "404", "Daño válvula",                      5, "ACU"),
    ("400", "405", "Daño hidrante",                     5, "ACU"),
    ("400", "406", "Rebose alcantarillado",             2, "ALC"),
    ("400", "407", "Obstrucción alcantarillado",        3, "ALC"),
    ("400", "408", "Colapso red",                       1, "ALC"),
    ("400", "409", "Falta mantenimiento",               10, "AMB"),
    ("500", "501", "Nueva conexión",                    15, "ACU"),
    ("500", "502", "Modificación conexión",             10, "ACU"),
    ("500", "503", "Traslado conexión",                 10, "ACU"),
    ("500", "504", "Viabilidad servicio",               15, "ACU"),
    ("500", "505", "Independización acometida",         15, "ACU"),
    ("600", "601", "Investigación fraude",              10, "ACU"),
    ("600", "602", "Manipulación medidor",              5,  "ACU"),
    ("600", "603", "Conexión ilegal",                   5,  "ACU"),
    ("600", "604", "Revisión acometida",                5,  "ACU"),
    ("600", "605", "Recuperación consumos",             10, "ACU"),
    ("600", "606", "Normalización servicio",            5,  "ACU"),
    ("700", "701", "Intermitencia servicio",            5,  "ACU"),
    ("700", "702", "Falta servicio",                    3,  "ACU"),
    ("700", "703", "Continuidad deficiente",            5,  "ACU"),
    ("700", "704", "Baja disponibilidad",               5,  "ACU"),
    ("700", "705", "Cobertura servicio",                10, "ACU"),
]

_SERIES_NOMBRES = {
    "100": "Calidad del Agua",
    "200": "Suspensión",
    "300": "Reconexión",
    "400": "Redes e Infraestructura",
    "500": "Conexiones",
    "600": "Fraudes",
    "700": "Servicio",
}


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
        # ── Tabla áreas institucionales ─────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS areas_institucionales (
                codigo      TEXT PRIMARY KEY,
                nombre      TEXT NOT NULL,
                orden       INTEGER DEFAULT 0,
                activo      INTEGER DEFAULT 1
            )
        """)
        for codigo, nombre, orden in _AREAS:
            conn.execute(
                "INSERT OR IGNORE INTO areas_institucionales (codigo,nombre,orden) VALUES (?,?,?)",
                (codigo, nombre, orden)
            )

        # ── Tabla subáreas ───────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subareas_institucionales (
                codigo       TEXT PRIMARY KEY,
                area_codigo  TEXT NOT NULL,
                nombre       TEXT NOT NULL,
                orden        INTEGER DEFAULT 0,
                activo       INTEGER DEFAULT 1
            )
        """)
        for codigo, area, nombre, orden in _SUBAREAS:
            conn.execute(
                "INSERT OR IGNORE INTO subareas_institucionales (codigo,area_codigo,nombre,orden) VALUES (?,?,?,?)",
                (codigo, area, nombre, orden)
            )

        # ── Series de causales PQRS ──────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pqrs_series_causales (
                codigo  TEXT PRIMARY KEY,
                nombre  TEXT NOT NULL,
                activo  INTEGER DEFAULT 1
            )
        """)
        for serie, nombre in _SERIES_NOMBRES.items():
            conn.execute(
                "INSERT OR IGNORE INTO pqrs_series_causales (codigo,nombre) VALUES (?,?)",
                (serie, nombre)
            )

        # ── Catálogo de causales RC6 ─────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pqrs_causales_rc6 (
                pk_causal_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                serie         TEXT NOT NULL,
                codigo        TEXT NOT NULL UNIQUE,
                nombre        TEXT NOT NULL,
                sla_dias      INTEGER DEFAULT 15,
                servicio      TEXT DEFAULT 'ACU',
                responsable   TEXT DEFAULT '',
                activo        INTEGER DEFAULT 1
            )
        """)
        for serie, codigo, nombre, sla, servicio in _CAUSALES_RC6:
            conn.execute("""
                INSERT OR IGNORE INTO pqrs_causales_rc6
                (serie, codigo, nombre, sla_dias, servicio)
                VALUES (?,?,?,?,?)
            """, (serie, codigo, nombre, sla, servicio))

        # ── Agregar columnas RC6 a tabla pqrs (si no existen) ───────────────
        cols_pqrs = {r[1] for r in conn.execute("PRAGMA table_info(pqrs)").fetchall()}
        nuevas_pqrs = {
            "servicio":         "TEXT DEFAULT 'ACU'",
            "tipo_solicitante_rc6": "TEXT DEFAULT 'suscriptor'",
            "medio_recepcion_rc6":  "TEXT DEFAULT 'presencial'",
            "causal_rc6":       "TEXT DEFAULT ''",
            "subarea_codigo":   "TEXT DEFAULT 'GC-02'",
        }
        for col, defn in nuevas_pqrs.items():
            if col not in cols_pqrs:
                conn.execute(f"ALTER TABLE pqrs ADD COLUMN {col} {defn}")
                _log.info("RC6 022: columna pqrs.%s agregada", col)

        # ── Tabla suscriptores_registro (vincula contactos con datos operativos) ─
        conn.execute("""
            CREATE TABLE IF NOT EXISTS suscriptores_registro (
                pk_sus_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_contacto_id   INTEGER NOT NULL UNIQUE,
                codigo_suscriptor TEXT,
                fecha_afiliacion  TEXT,
                estado_servicio   TEXT DEFAULT 'activo',
                tipo_predio       TEXT DEFAULT 'residencial',
                estrato           INTEGER DEFAULT 1,
                area_predio_m2    REAL,
                subarea_codigo    TEXT DEFAULT 'GC-01',
                fecha_ultima_noved TEXT,
                observaciones     TEXT DEFAULT '',
                FOREIGN KEY (fk_contacto_id) REFERENCES contactos(pk_contacto_id)
            )
        """)

        # ── Tabla inventario_items ───────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inventario_items (
                pk_item_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo        TEXT NOT NULL UNIQUE,
                nombre        TEXT NOT NULL,
                categoria     TEXT DEFAULT 'material',
                unidad        TEXT DEFAULT 'und',
                existencia    REAL DEFAULT 0,
                existencia_min REAL DEFAULT 0,
                ubicacion     TEXT DEFAULT '',
                subarea_codigo TEXT DEFAULT 'GF-05',
                activo        INTEGER DEFAULT 1,
                fecha_creacion TEXT DEFAULT (date('now'))
            )
        """)

        # ── Tabla inventario_movimientos ────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inventario_movimientos (
                pk_mov_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_item_id    INTEGER NOT NULL,
                tipo_mov      TEXT NOT NULL CHECK(tipo_mov IN ('ENTRADA','SALIDA','AJUSTE')),
                cantidad      REAL NOT NULL,
                existencia_post REAL,
                fecha         TEXT NOT NULL,
                responsable   TEXT DEFAULT '',
                concepto      TEXT DEFAULT '',
                fk_ot_id      INTEGER,
                fecha_registro TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (fk_item_id) REFERENCES inventario_items(pk_item_id)
            )
        """)

        # ── Índices ──────────────────────────────────────────────────────────
        indices = [
            ("idx_pqrs_causal_rc6", "pqrs(causal_rc6)"),
            ("idx_pqrs_servicio",   "pqrs(servicio)"),
            ("idx_inv_item",        "inventario_movimientos(fk_item_id)"),
            ("idx_sus_contacto",    "suscriptores_registro(fk_contacto_id)"),
        ]
        tablas_exist = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        for idx, target in indices:
            tabla = target.split("(")[0].strip()
            if tabla in tablas_exist:
                try:
                    conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {target}")
                except Exception as ei:
                    _log.warning("RC6 022: índice %s omitido: %s", idx, ei)

        conn.commit()
        _log.info("Migración 022 RC6: áreas, subáreas, causales RC6, suscriptores, inventarios creados.")
        return True
    except Exception as e:
        conn.rollback()
        _log.error("migrar_022: %s", e, exc_info=True)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    sys.exit(0 if migrar(sys.argv[1] if len(sys.argv) > 1 else None) else 1)
