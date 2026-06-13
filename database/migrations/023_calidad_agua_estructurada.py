"""
database/migrations/023_calidad_agua_estructurada.py
RC6 GA-02 — Módulo de Calidad de Agua estructurado (no texto libre).
Parámetros con norma colombiana, resultado ACEPTABLE/NO_ACEPTABLE,
acciones correctivas cuando no acepta.
Idempotente.
"""
import sqlite3, os, logging

_log = logging.getLogger("sigca.migrations")

_PARAMETROS_DEFAULT = [
    # (codigo, nombre, unidad, valor_min, valor_max, norma, orden)
    ("pH",       "pH",                "",      6.5, 9.0, "Res. 2115/2007", 1),
    ("CLORO",    "Cloro Residual",    "mg/L",  0.3, 2.0, "Res. 2115/2007", 2),
    ("TURB",     "Turbiedad",         "UNT",   0.0, 2.0, "Res. 2115/2007", 3),
    ("COLOR",    "Color Aparente",    "UPC",   0.0, 15.0,"Res. 2115/2007", 4),
    ("COND",     "Conductividad",     "µS/cm", 0.0,1000.0,"Res. 2115/2007",5),
    ("OLOR",     "Olor",              "",      0.0, 0.0, "Res. 2115/2007", 6),
    ("SABOR",    "Sabor",             "",      0.0, 0.0, "Res. 2115/2007", 7),
    ("COLIF",    "Coliformes Totales","UFC/100mL",0.0,0.0,"Res. 2115/2007",8),
    ("ECOLI",    "E. coli",           "UFC/100mL",0.0,0.0,"Res. 2115/2007",9),
    ("NITRATOS", "Nitratos",          "mg/L",  0.0,10.0, "Res. 2115/2007",10),
    ("FLUORUROS","Fluoruros",         "mg/L",  0.0, 1.0, "Res. 2115/2007",11),
]


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
        # ── Parámetros configurables ─────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS calidad_parametros (
                pk_param_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo       TEXT NOT NULL UNIQUE,
                nombre       TEXT NOT NULL,
                unidad       TEXT DEFAULT '',
                valor_min    REAL,
                valor_max    REAL,
                norma        TEXT DEFAULT 'Res. 2115/2007',
                orden        INTEGER DEFAULT 0,
                activo       INTEGER DEFAULT 1
            )
        """)
        for codigo, nombre, unidad, vmin, vmax, norma, orden in _PARAMETROS_DEFAULT:
            conn.execute("""
                INSERT OR IGNORE INTO calidad_parametros
                (codigo, nombre, unidad, valor_min, valor_max, norma, orden)
                VALUES (?,?,?,?,?,?,?)
            """, (codigo, nombre, unidad, vmin, vmax, norma, orden))

        # ── Puntos de muestreo ───────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS calidad_puntos_muestreo (
                pk_punto_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo        TEXT NOT NULL UNIQUE,
                nombre        TEXT NOT NULL,
                tipo          TEXT DEFAULT 'distribucion',
                descripcion   TEXT DEFAULT '',
                coordenada_lat REAL,
                coordenada_lon REAL,
                activo        INTEGER DEFAULT 1
            )
        """)

        # ── Muestras (cabecera) ──────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS calidad_muestras (
                pk_muestra_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_muestra  TEXT NOT NULL UNIQUE,
                anio            INTEGER NOT NULL,
                mes             INTEGER NOT NULL,
                fecha_muestra   TEXT NOT NULL,
                fk_punto_id     INTEGER,
                laboratorio     TEXT DEFAULT '',
                responsable     TEXT DEFAULT '',
                observaciones   TEXT DEFAULT '',
                estado          TEXT DEFAULT 'registrada',
                subarea_codigo  TEXT DEFAULT 'GA-02',
                fecha_registro  TEXT DEFAULT (datetime('now')),
                registrado_por  TEXT DEFAULT '',
                FOREIGN KEY (fk_punto_id) REFERENCES calidad_puntos_muestreo(pk_punto_id)
            )
        """)

        # ── Resultados por parámetro ─────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS calidad_resultados (
                pk_resultado_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_muestra_id    INTEGER NOT NULL,
                fk_param_id      INTEGER NOT NULL,
                resultado        TEXT DEFAULT 'ACEPTABLE'
                                 CHECK(resultado IN ('ACEPTABLE','NO_ACEPTABLE','NO_MEDIDO')),
                valor_obtenido   REAL,
                unidad_medida    TEXT DEFAULT '',
                valor_permitido  TEXT DEFAULT '',
                observacion      TEXT DEFAULT '',
                accion_correctiva TEXT DEFAULT '',
                fecha_registro   TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (fk_muestra_id) REFERENCES calidad_muestras(pk_muestra_id),
                FOREIGN KEY (fk_param_id)   REFERENCES calidad_parametros(pk_param_id),
                UNIQUE (fk_muestra_id, fk_param_id)
            )
        """)

        # ── Índices ──────────────────────────────────────────────────────────
        for idx, target in [
            ("idx_cal_muestra_anio_mes",  "calidad_muestras(anio, mes)"),
            ("idx_cal_resultado_muestra", "calidad_resultados(fk_muestra_id)"),
            ("idx_cal_resultado_param",   "calidad_resultados(fk_param_id)"),
        ]:
            try:
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {target}")
            except Exception as ei:
                _log.warning("023: índice %s omitido: %s", idx, ei)

        conn.commit()
        _log.info("Migración 023: calidad_agua estructurada (parametros, muestras, resultados) creada.")
        return True
    except Exception as e:
        conn.rollback()
        _log.error("migrar_023: %s", e, exc_info=True)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    sys.exit(0 if migrar(sys.argv[1] if len(sys.argv) > 1 else None) else 1)
