"""
database/migrations/021_tipos_proyecto_e_indices.py
Crea tabla tipos_proyecto configurable y agrega indices de rendimiento
para tareas_proyecto, metas_proyecto y documentos_proyecto.
Idempotente.
"""
import sqlite3, os, logging

_log = logging.getLogger("sigca.migrations")

_TIPOS_INICIALES = [
    ("pueaa", "PUEAA - Plan de Uso Eficiente de Agua", 1),
    ("psmv",  "PSMV - Plan de Saneamiento y Manejo de Vertimientos", 2),
    ("sspd",  "SSPD - Superintendencia de Servicios", 3),
    ("obra",  "Obra de infraestructura", 4),
    ("otro",  "Otro tipo de proyecto", 99),
]

_INDICES = [
    ("idx_tareas_proyecto_id",   "tareas_proyecto(proyecto_id)"),
    ("idx_tareas_estado_proy",   "tareas_proyecto(estado)"),
    ("idx_metas_proyecto_id",    "metas_proyecto(proyecto_id)"),
    ("idx_docs_proy_proyecto",   "documentos_proyecto(proyecto_id)"),
    ("idx_docs_proy_documento",  "documentos_proyecto(documento_id)"),
    ("idx_costos_proyecto_id",   "costos_reales(proyecto_id)"),
    ("idx_ingresos_proyecto_id", "ingresos(proyecto_id)"),
    ("idx_riesgos_proyecto_id",  "riesgos_proyecto(proyecto_id)"),
    ("idx_proyectos_estado_tipo","proyectos(estado, tipo_proyecto)"),
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
    try:
        # Tabla de tipos de proyecto configurable
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tipos_proyecto (
                pk_tipo_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo      TEXT NOT NULL UNIQUE,
                nombre      TEXT NOT NULL,
                descripcion TEXT DEFAULT '',
                orden       INTEGER DEFAULT 0,
                activo      INTEGER DEFAULT 1
            )
        """)
        for codigo, nombre, orden in _TIPOS_INICIALES:
            conn.execute("""
                INSERT OR IGNORE INTO tipos_proyecto (codigo, nombre, orden)
                VALUES (?,?,?)
            """, (codigo, nombre, orden))

        # Indices de rendimiento — solo sobre tablas existentes
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        for idx_name, idx_target in _INDICES:
            tabla = idx_target.split("(")[0].strip()
            if tabla not in tablas:
                _log.info("Migracion 021: tabla '%s' no existe, omitiendo indice %s", tabla, idx_name)
                continue
            try:
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_target}")
            except Exception as ei:
                _log.warning("Migracion 021: indice %s omitido: %s", idx_name, ei)

        conn.commit()
        _log.info("Migracion 021: tipos_proyecto + indices aplicados.")
        return True
    except Exception as e:
        conn.rollback()
        _log.error("migrar_021: %s", e, exc_info=True)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    sys.exit(0 if migrar(sys.argv[1] if len(sys.argv) > 1 else None) else 1)
