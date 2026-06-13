"""
database/migrations/019_indices_rendimiento.py
Indices de rendimiento para las consultas mas frecuentes.
Idempotente — CREATE INDEX IF NOT EXISTS.
"""
import sqlite3, os, logging

_log = logging.getLogger("sigca.migrations")

_INDICES = [
    ("idx_rc_estado",     "registro_central(estado)"),
    ("idx_rc_area",       "registro_central(area)"),
    ("idx_rc_fecha_rad",  "registro_central(fecha_radicacion DESC)"),
    ("idx_rc_creado_por", "registro_central(creado_por)"),
    ("idx_pqrs_estado",   "pqrs(estado_pqr)"),
    ("idx_pqrs_limite",   "pqrs(fecha_limite)"),
    ("idx_pqrs_tipo",     "pqrs(tipo_pqr)"),
    ("idx_proy_estado",   "proyectos(estado)"),
    ("idx_proy_respons",  "proyectos(responsable_id)"),
    ("idx_contactos_rs",  "contactos(razon_social)"),
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
    created = 0
    try:
        for idx_name, idx_target in _INDICES:
            try:
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_target}")
                created += 1
            except Exception as ei:
                _log.warning("Indice %s omitido: %s", idx_name, ei)
        conn.commit()
        _log.info("Migracion 019: %d indices verificados.", created)
        return True
    except Exception as e:
        conn.rollback()
        _log.error("migrar_019: %s", e, exc_info=True)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    sys.exit(0 if migrar(sys.argv[1] if len(sys.argv) > 1 else None) else 1)
