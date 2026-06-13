"""
029_personal_gl01.py — GL-01 Personal básico.
030_comprobantes_gf02.py — GF-02 Tesorería: Comprobantes ingreso/egreso.
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

    # GL-01 Personal
    if "gl_personal" not in tablas:
        conn.execute("""
            CREATE TABLE gl_personal (
                pk_personal_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_contacto_id  INTEGER,
                cargo           TEXT NOT NULL,
                tipo_contrato   TEXT DEFAULT 'TERMINO_INDEFINIDO'
                    CHECK(tipo_contrato IN ('TERMINO_FIJO','TERMINO_INDEFINIDO',
                                            'PRESTACION_SERVICIOS','OBRA_LABOR')),
                fecha_ingreso   TEXT,
                fecha_retiro    TEXT,
                salario_base    REAL DEFAULT 0,
                estado          TEXT DEFAULT 'ACTIVO'
                    CHECK(estado IN ('ACTIVO','INACTIVO','LICENCIA')),
                numero_contrato TEXT,
                eps             TEXT,
                arl             TEXT,
                fondo_pension   TEXT,
                observaciones   TEXT,
                usuario         TEXT,
                fecha_creacion  TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_gl_personal_estado ON gl_personal(estado)")
        conn.execute("CREATE INDEX idx_gl_personal_cargo  ON gl_personal(cargo)")

    # GF-02 Comprobantes de tesorería
    if "gf_comprobantes" not in tablas:
        conn.execute("""
            CREATE TABLE gf_comprobantes (
                pk_comp_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo            TEXT NOT NULL
                    CHECK(tipo IN ('INGRESO','EGRESO')),
                numero          TEXT NOT NULL,
                fecha           TEXT NOT NULL,
                concepto        TEXT NOT NULL,
                valor           REAL NOT NULL,
                beneficiario    TEXT,
                fk_banco_id     INTEGER,
                medio_pago      TEXT DEFAULT 'TRANSFERENCIA'
                    CHECK(medio_pago IN ('EFECTIVO','TRANSFERENCIA','CHEQUE','OTRO')),
                estado          TEXT DEFAULT 'BORRADOR'
                    CHECK(estado IN ('BORRADOR','APROBADO','ANULADO')),
                aprobado_por    TEXT,
                fecha_aprobacion TEXT,
                fk_trans_id     INTEGER,
                observaciones   TEXT,
                usuario         TEXT,
                fecha_creacion  TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_gf_comp_tipo   ON gf_comprobantes(tipo)")
        conn.execute("CREATE INDEX idx_gf_comp_fecha  ON gf_comprobantes(fecha)")
        conn.execute("CREATE INDEX idx_gf_comp_estado ON gf_comprobantes(estado)")
        # Consecutivos por año para comprobantes
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gf_consecutivos_comp (
                anio      INTEGER NOT NULL,
                tipo      TEXT NOT NULL,
                ultimo    INTEGER DEFAULT 0,
                PRIMARY KEY(anio, tipo)
            )
        """)

    conn.commit()
    conn.close()
