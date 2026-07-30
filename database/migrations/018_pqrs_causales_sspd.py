"""
database/migrations/018_pqrs_causales_sspd.py
Crea tabla pqrs_causales_sspd con la clasificacion F/I/P/O de la Res. SSPD 54575/2015.
Idempotente.
"""
import sqlite3, os, logging

_log = logging.getLogger("sigca.migrations")

_CAUSALES_SSPD = [
    # (grupo, codigo_sui, nombre, normativa)
    ("F", "01", "Facturacion",              "Res. SSPD 54575/2015 Art. 8"),
    ("F", "06", "Medidores",                "Ley 142 Art. 146"),
    ("F", "10", "Cobros no reconocidos",    "Ley 142 Art. 148"),
    ("I", "04", "Conexion del servicio",    "Ley 142 Art. 134"),
    ("I", "05", "Reconexion del servicio",  "Ley 142 Art. 140"),
    ("P", "02", "Calidad del servicio",     "Resolucion 2115/2007"),
    ("P", "03", "Suspension del servicio",  "Ley 142 Art. 136"),
    ("P", "09", "Danos a terceros",         "Ley 142 Art. 136"),
    ("O", "07", "Contrato / Condiciones",   "Ley 142 Art. 133"),
    ("O", "08", "Atencion al cliente",      "Ley 142"),
    ("O", "11", "Terminacion del contrato", "Ley 142"),
    ("O", "12", "Cesion de inmueble",       "Ley 142"),
    ("O", "99", "Otras causales",           "Res. SSPD 54575/2015"),
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pqrs_causales_sspd (
                pk_id         INTEGER PRIMARY KEY AUTOINCREMENT,
                grupo_codigo  TEXT NOT NULL,
                codigo_sui    TEXT NOT NULL UNIQUE,
                nombre        TEXT NOT NULL,
                normativa     TEXT DEFAULT '',
                activo        INTEGER DEFAULT 1
            )
        """)
        for g, c, n, norm in _CAUSALES_SSPD:
            conn.execute("""
                INSERT OR IGNORE INTO pqrs_causales_sspd
                (grupo_codigo, codigo_sui, nombre, normativa)
                VALUES (?,?,?,?)
            """, (g, c, n, norm))
        conn.commit()
        _log.info("Migracion 018: tabla pqrs_causales_sspd creada/verificada.")
        return True
    except Exception as e:
        conn.rollback()
        _log.error("migrar_018: %s", e, exc_info=True)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    sys.exit(0 if migrar(sys.argv[1] if len(sys.argv) > 1 else None) else 1)
