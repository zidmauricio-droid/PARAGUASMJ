"""
025_plan_cuentas_financiero.py
Plan de cuentas jerárquico + transacciones con seguimiento de pago + presupuesto.
Basado en estructura Excel PC_rec/PC_des/JAN../META.
Idempotente.
"""
import sqlite3


def migrar(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    tablas = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    # ── Plan de Cuentas ───────────────────────────────────────────────
    if "fin_plan_cuentas" not in tablas:
        conn.execute("""
            CREATE TABLE fin_plan_cuentas (
                pk_cuenta_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo          TEXT NOT NULL UNIQUE,
                nombre          TEXT NOT NULL,
                tipo            TEXT NOT NULL CHECK(tipo IN ('INGRESO','GASTO')),
                nivel           INTEGER DEFAULT 1,
                codigo_padre    TEXT,
                activo          INTEGER DEFAULT 1,
                orden           INTEGER DEFAULT 0
            )
        """)
        # Ingresos
        ingresos = [
            ("1",   "INGRESOS",                     "INGRESO", 0, None,  0),
            ("1.1", "Ingresos con Productos",        "INGRESO", 1, "1",   10),
            ("1.1.1","Ventas garrafones",             "INGRESO", 2, "1.1", 11),
            ("1.1.2","Ventas tanques / accesorios",   "INGRESO", 2, "1.1", 12),
            ("1.1.3","Ventas medidores",              "INGRESO", 2, "1.1", 13),
            ("1.2", "Ingresos con Servicios",         "INGRESO", 1, "1",   20),
            ("1.2.1","Recaudo tarifa mensual",         "INGRESO", 2, "1.2", 21),
            ("1.2.2","Nueva conexion",                "INGRESO", 2, "1.2", 22),
            ("1.2.3","Reconexion",                    "INGRESO", 2, "1.2", 23),
            ("1.3", "Ingresos No Operacionales",      "INGRESO", 1, "1",   30),
            ("1.3.1","Cuota extraordinaria",          "INGRESO", 2, "1.3", 31),
            ("1.3.2","Intereses recibidos",           "INGRESO", 2, "1.3", 32),
            ("1.3.3","Otros ingresos",                "INGRESO", 2, "1.3", 33),
        ]
        # Gastos
        gastos = [
            ("2",   "GASTOS",                         "GASTO", 0, None,  0),
            ("2.1", "Gastos con Productos",            "GASTO", 1, "2",   10),
            ("2.1.1","Quimicos / cloro",               "GASTO", 2, "2.1", 11),
            ("2.1.2","Accesorios PVC / tuberia",       "GASTO", 2, "2.1", 12),
            ("2.1.3","Repuestos equipos",              "GASTO", 2, "2.1", 13),
            ("2.2", "Gastos con Servicios",            "GASTO", 1, "2",   20),
            ("2.2.1","Gasolina / combustible",         "GASTO", 2, "2.2", 21),
            ("2.2.2","Transporte / acarreos",          "GASTO", 2, "2.2", 22),
            ("2.2.3","Hospedaje / viaticos",           "GASTO", 2, "2.2", 23),
            ("2.2.4","Servicios profesionales",        "GASTO", 2, "2.2", 24),
            ("2.3", "Gastos No Operacionales",         "GASTO", 1, "2",   30),
            ("2.3.1","Costos financieros / intereses", "GASTO", 2, "2.3", 31),
            ("2.3.2","Comisiones bancarias",           "GASTO", 2, "2.3", 32),
            ("2.4", "Gastos con RH",                  "GASTO", 1, "2",   40),
            ("2.4.1","Sueldos / salarios",             "GASTO", 2, "2.4", 41),
            ("2.4.2","Bonificaciones",                 "GASTO", 2, "2.4", 42),
            ("2.4.3","Cesantias / prestaciones",       "GASTO", 2, "2.4", 43),
            ("2.5", "Gastos Operacionales",            "GASTO", 1, "2",   50),
            ("2.5.1","Alquiler",                      "GASTO", 2, "2.5", 51),
            ("2.5.2","Telecomunicaciones",             "GASTO", 2, "2.5", 52),
            ("2.5.3","Energia electrica",              "GASTO", 2, "2.5", 53),
            ("2.6", "Dotacion / Marketing",            "GASTO", 1, "2",   60),
            ("2.6.1","EPP / uniformes",                "GASTO", 2, "2.6", 61),
            ("2.6.2","Publicidad / difusion",          "GASTO", 2, "2.6", 62),
            ("2.7", "Impuestos y Transferencias",      "GASTO", 1, "2",   70),
            ("2.7.1","TUA / TR / estampillas",         "GASTO", 2, "2.7", 71),
            ("2.7.2","IVA no descontable",             "GASTO", 2, "2.7", 72),
            ("2.7.3","Consignaciones / traslados",     "GASTO", 2, "2.7", 73),
            ("2.8", "Papeleria e Inversiones",         "GASTO", 1, "2",   80),
            ("2.8.1","Papeleria / toner",              "GASTO", 2, "2.8", 81),
            ("2.8.2","Equipos / maquinaria",           "GASTO", 2, "2.8", 82),
            ("2.8.3","Software / licencias",           "GASTO", 2, "2.8", 83),
        ]
        for row in ingresos + gastos:
            conn.execute(
                "INSERT OR IGNORE INTO fin_plan_cuentas "
                "(codigo, nombre, tipo, nivel, codigo_padre, orden) VALUES (?,?,?,?,?,?)",
                row
            )

    # ── Transacciones mensuales ───────────────────────────────────────
    if "fin_transacciones" not in tablas:
        conn.execute("""
            CREATE TABLE fin_transacciones (
                pk_trans_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                anio            INTEGER NOT NULL,
                mes             INTEGER NOT NULL CHECK(mes BETWEEN 1 AND 12),
                fecha_registro  TEXT NOT NULL,
                cod_cuenta      TEXT NOT NULL,
                descripcion     TEXT NOT NULL,
                valor           REAL NOT NULL,
                tipo            TEXT NOT NULL CHECK(tipo IN ('INGRESO','GASTO')),
                fecha_pago      TEXT,
                estado_pago     TEXT DEFAULT 'PENDIENTE' CHECK(estado_pago IN ('PAGADO','PENDIENTE','NO_APLICA')),
                es_recurrente   INTEGER DEFAULT 0,
                meses_recurrencia TEXT,
                observacion     TEXT,
                fk_banco_id     INTEGER,
                usuario         TEXT,
                fecha_creacion  TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_fin_trans_anio_mes ON fin_transacciones(anio, mes)")
        conn.execute("CREATE INDEX idx_fin_trans_cuenta ON fin_transacciones(cod_cuenta)")
        conn.execute("CREATE INDEX idx_fin_trans_pago ON fin_transacciones(estado_pago)")

    # ── Presupuesto / Meta anual ──────────────────────────────────────
    if "fin_presupuesto" not in tablas:
        conn.execute("""
            CREATE TABLE fin_presupuesto (
                pk_pres_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                anio            INTEGER NOT NULL,
                mes             INTEGER NOT NULL CHECK(mes BETWEEN 1 AND 12),
                cod_cuenta      TEXT NOT NULL,
                valor_meta      REAL NOT NULL DEFAULT 0,
                UNIQUE(anio, mes, cod_cuenta)
            )
        """)

    conn.commit()
    conn.close()
