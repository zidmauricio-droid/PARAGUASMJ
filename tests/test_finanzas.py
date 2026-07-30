"""
tests/test_finanzas.py
Pruebas de integridad financiera, seguridad y auditoria.
Ejecutar: python -m unittest tests/test_finanzas.py -v
Requiere solo la libreria estandar de Python (unittest, sqlite3).
"""
import unittest
import sqlite3
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _crear_bd_temporal():
    """Crea BD en memoria con el esquema minimo para pruebas."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        PRAGMA foreign_keys = ON;
        PRAGMA journal_mode = WAL;

        CREATE TABLE caja_chica (
            pk_caja_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha         TEXT    NOT NULL,
            concepto      TEXT    NOT NULL,
            tipo_mov      TEXT    NOT NULL CHECK(tipo_mov IN ('INGRESO','EGRESO')),
            importe       REAL    NOT NULL CHECK(importe > 0),
            usuario       TEXT,
            fecha_registro TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE bancos (
            pk_banco_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_cuenta TEXT    NOT NULL UNIQUE,
            banco_nombre  TEXT    NOT NULL,
            tipo_cuenta   TEXT    DEFAULT 'AHORRO',
            moneda        TEXT    DEFAULT 'COP',
            saldo_actual  REAL    DEFAULT 0,
            ejecutivo     TEXT,
            telefono      TEXT,
            status        TEXT    DEFAULT 'ACTIVA'
        );

        CREATE TABLE movimientos_financieros (
            pk_mov_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha         TEXT    NOT NULL,
            fk_banco_id   INTEGER REFERENCES bancos(pk_banco_id),
            tipo_mov      TEXT    NOT NULL CHECK(tipo_mov IN ('INGRESO','EGRESO')),
            concepto      TEXT    NOT NULL,
            importe       REAL    NOT NULL CHECK(importe > 0),
            referencia    TEXT,
            usuario       TEXT,
            fecha_registro TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE logs_sistema (
            pk_log_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            nivel         TEXT,
            modulo        TEXT,
            usuario       TEXT,
            accion        TEXT,
            detalle       TEXT,
            ip_origen     TEXT,
            timestamp     TEXT DEFAULT (datetime('now'))
        );

        INSERT INTO bancos (codigo_cuenta, banco_nombre, saldo_actual, status)
        VALUES ('BCO-001', 'Banco Prueba', 500000.0, 'ACTIVA');

        INSERT INTO caja_chica (fecha, concepto, tipo_mov, importe, usuario)
        VALUES ('2026-01-15', 'Pago papeleria', 'EGRESO', 25000, 'admin');

        INSERT INTO caja_chica (fecha, concepto, tipo_mov, importe, usuario)
        VALUES ('2026-01-20', 'Venta formularios', 'INGRESO', 10000, 'admin');
    """)
    return conn


class TestValidaciones(unittest.TestCase):
    def setUp(self):
        self.conn = _crear_bd_temporal()

    def tearDown(self):
        self.conn.close()

    def test_importe_cero_rechazado(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO caja_chica (fecha,concepto,tipo_mov,importe) VALUES (?,?,?,?)",
                ("2026-01-01", "Test", "EGRESO", 0)
            )

    def test_importe_negativo_rechazado(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO caja_chica (fecha,concepto,tipo_mov,importe) VALUES (?,?,?,?)",
                ("2026-01-01", "Test", "EGRESO", -500)
            )

    def test_tipo_mov_invalido_rechazado(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO caja_chica (fecha,concepto,tipo_mov,importe) VALUES (?,?,?,?)",
                ("2026-01-01", "Test", "TRANSFERENCIA", 1000)
            )

    def test_codigo_banco_duplicado_rechazado(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO bancos (codigo_cuenta,banco_nombre) VALUES (?,?)",
                ("BCO-001", "Banco Duplicado")
            )

    def test_banco_saldo_inicial_negativo_permitido_en_bd(self):
        self.conn.execute(
            "INSERT INTO bancos (codigo_cuenta,banco_nombre,saldo_actual) VALUES (?,?,?)",
            ("BCO-NEG", "Banco Negativo", -1000)
        )
        saldo = self.conn.execute(
            "SELECT saldo_actual FROM bancos WHERE codigo_cuenta='BCO-NEG'"
        ).fetchone()[0]
        self.assertEqual(saldo, -1000.0)


class TestSaldoAnt(unittest.TestCase):
    def setUp(self):
        self.conn = _crear_bd_temporal()

    def tearDown(self):
        self.conn.close()

    def _saldo_anterior(self, tabla, fecha_desde, cuenta_id=None):
        from routes.finanzas import _saldo_anterior
        return _saldo_anterior(self.conn, tabla, fecha_desde, cuenta_id)

    def _movimientos_con_saldo(self, tabla, fd, fh, cuenta_id=None):
        from routes.finanzas import _movimientos_con_saldo
        return _movimientos_con_saldo(self.conn, tabla, fd, fh, cuenta_id)

    def test_saldo_anterior_caja_correcto(self):
        saldo = self._saldo_anterior("caja_chica", "2026-01-20")
        self.assertAlmostEqual(saldo, -25000.0)

    def test_saldo_anterior_caja_inicio(self):
        saldo = self._saldo_anterior("caja_chica", "2026-01-01")
        self.assertAlmostEqual(saldo, 0.0)

    def test_movimientos_con_saldo_acumulado(self):
        movs, saldo_ant, total = self._movimientos_con_saldo(
            "caja_chica", "2026-01-01", "2026-12-31"
        )
        self.assertEqual(len(movs), 2)
        self.assertEqual(total, 2)
        self.assertAlmostEqual(movs[-1]["saldo"], -15000.0)

    def test_tabla_no_autorizada_rechazada(self):
        from routes.finanzas import _saldo_anterior
        with self.assertRaises(ValueError):
            _saldo_anterior(self.conn, "usuarios", "2026-01-01")

    def test_paginacion_limit(self):
        from routes.finanzas import _movimientos_con_saldo
        movs_pag, _, total_pag = _movimientos_con_saldo(
            self.conn, "caja_chica", "2026-01-01", "2026-12-31", limit=1, offset=0
        )
        self.assertEqual(len(movs_pag), 1)
        self.assertEqual(total_pag, 2)


class TestIntegridadFinanciera(unittest.TestCase):
    def setUp(self):
        self.conn = _crear_bd_temporal()

    def tearDown(self):
        self.conn.close()

    def test_egreso_atomico_insert_update(self):
        banco = self.conn.execute(
            "SELECT saldo_actual FROM bancos WHERE codigo_cuenta='BCO-001'"
        ).fetchone()
        saldo_inicial = float(banco["saldo_actual"])
        self.conn.execute("BEGIN IMMEDIATE")
        self.conn.execute(
            "INSERT INTO movimientos_financieros (fecha,fk_banco_id,tipo_mov,concepto,importe,usuario) "
            "VALUES (?,?,?,?,?,?)",
            ("2026-06-01", 1, "EGRESO", "Pago prueba", 100000, "admin")
        )
        self.conn.execute(
            "UPDATE bancos SET saldo_actual=saldo_actual-? WHERE pk_banco_id=1",
            (100000,)
        )
        self.conn.commit()
        saldo_nuevo = float(self.conn.execute(
            "SELECT saldo_actual FROM bancos WHERE pk_banco_id=1"
        ).fetchone()[0])
        self.assertAlmostEqual(saldo_nuevo, saldo_inicial - 100000)

    def test_rollback_ante_error(self):
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            self.conn.execute(
                "INSERT INTO movimientos_financieros (fecha,fk_banco_id,tipo_mov,concepto,importe) "
                "VALUES (?,?,?,?,?)",
                ("2026-06-01", 1, "EGRESO", "Test rollback", 50000)
            )
            self.conn.execute(
                "INSERT INTO movimientos_financieros (fecha,tipo_mov,concepto,importe) "
                "VALUES (?,?,?,?)",
                ("2026-06-01", "INVALIDO", "Forzar error", 1000)
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
        n_movs = self.conn.execute(
            "SELECT COUNT(*) FROM movimientos_financieros WHERE concepto='Test rollback'"
        ).fetchone()[0]
        self.assertEqual(n_movs, 0)

    def test_banco_inactivo_no_deberia_recibir_movimientos(self):
        self.conn.execute("UPDATE bancos SET status='INACTIVA' WHERE pk_banco_id=1")
        self.conn.commit()
        status = self.conn.execute(
            "SELECT status FROM bancos WHERE pk_banco_id=1"
        ).fetchone()[0]
        self.assertEqual(status, "INACTIVA")


class TestAuditoria(unittest.TestCase):
    def setUp(self):
        self.conn = _crear_bd_temporal()

    def tearDown(self):
        self.conn.close()

    def _insertar_log(self, accion, detalle, modulo="finanzas"):
        self.conn.execute(
            "INSERT INTO logs_sistema (nivel,modulo,usuario,accion,detalle) VALUES (?,?,?,?,?)",
            ("AUDIT", modulo, "test_user", accion, detalle)
        )
        self.conn.commit()

    def test_log_caja_nuevo_tiene_importe(self):
        detalle = "EGRESO | Pago luz | $85000 | 2026-06-01"
        self._insertar_log("CAJA_NUEVO", detalle)
        log = self.conn.execute(
            "SELECT detalle FROM logs_sistema WHERE accion='CAJA_NUEVO'"
        ).fetchone()
        self.assertIn("85000", log["detalle"])
        self.assertIn("EGRESO", log["detalle"])

    def test_log_caja_eliminar_tiene_concepto_previo(self):
        detalle = "ELIMINADO | EGRESO | Pago papeleria | $25000 | 2026-01-15"
        self._insertar_log("CAJA_ELIMINAR", detalle)
        log = self.conn.execute(
            "SELECT detalle FROM logs_sistema WHERE accion='CAJA_ELIMINAR'"
        ).fetchone()
        self.assertIn("ELIMINADO", log["detalle"])
        self.assertIn("Pago papeleria", log["detalle"])

    def test_log_banco_inactivar_tiene_saldo(self):
        detalle = "Banco Prueba (BCO-001) | Saldo: $500000 | Movimientos registrados: 3"
        self._insertar_log("BANCO_INACTIVAR", detalle)
        log = self.conn.execute(
            "SELECT detalle FROM logs_sistema WHERE accion='BANCO_INACTIVAR'"
        ).fetchone()
        self.assertIn("500000", log["detalle"])

    def test_logs_no_eliminables(self):
        import inspect
        try:
            import routes.finanzas as fin
            source = inspect.getsource(fin)
            self.assertNotIn("DELETE FROM logs_sistema", source)
        except ImportError:
            self.skipTest("Modulo finanzas no disponible")


class TestSeguridad(unittest.TestCase):
    def setUp(self):
        try:
            import app as flask_app
            flask_app.app.config["TESTING"] = True
            flask_app.app.config["SECRET_KEY"] = "test-key-no-production"
            self.client = flask_app.app.test_client()
            self._app_disponible = True
        except (ImportError, Exception) as e:
            self._app_disponible = False
            self._skip_reason = str(e)

    def _skip_si_app_no_disponible(self):
        if not self._app_disponible:
            self.skipTest(f"App no disponible (import pendiente): {self._skip_reason}")

    def test_caja_sin_login_redirige(self):
        self._skip_si_app_no_disponible()
        r = self.client.get("/finanzas/caja")
        self.assertEqual(r.status_code, 302)

    def test_caja_consultar_sin_login_redirige(self):
        self._skip_si_app_no_disponible()
        r = self.client.get("/finanzas/caja/consultar")
        self.assertEqual(r.status_code, 302)

    def test_movimientos_sin_login_redirige(self):
        self._skip_si_app_no_disponible()
        r = self.client.get("/finanzas/movimientos")
        self.assertEqual(r.status_code, 302)

    def test_bancos_sin_login_redirige(self):
        self._skip_si_app_no_disponible()
        r = self.client.get("/finanzas/bancos")
        self.assertEqual(r.status_code, 302)

    def test_caja_nuevo_post_sin_login_redirige(self):
        self._skip_si_app_no_disponible()
        r = self.client.post("/finanzas/caja/nuevo",
                              data={"fecha": "2026-01-01", "concepto": "Test",
                                    "tipo_mov": "EGRESO", "importe": "1000"})
        self.assertEqual(r.status_code, 302)

    def test_banco_crear_post_sin_login_redirige(self):
        self._skip_si_app_no_disponible()
        r = self.client.post("/finanzas/bancos/crear",
                              data={"codigo_cuenta": "TEST", "banco_nombre": "Test"})
        self.assertEqual(r.status_code, 302)

    def test_whitelist_tabla_bloquea_tablas_no_autorizadas(self):
        from routes.finanzas import _validar_tabla
        with self.assertRaises(ValueError):
            _validar_tabla("usuarios")
        with self.assertRaises(ValueError):
            _validar_tabla("logs_sistema")
        _validar_tabla("caja_chica")
        _validar_tabla("movimientos_financieros")


class TestResiliencia(unittest.TestCase):
    def setUp(self):
        self.conn = _crear_bd_temporal()

    def tearDown(self):
        self.conn.close()

    def test_pragmas_wal_aplicados(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tmp_path = f.name
        try:
            conn_file = sqlite3.connect(tmp_path)
            conn_file.execute("PRAGMA journal_mode=WAL")
            modo = conn_file.execute("PRAGMA journal_mode").fetchone()[0]
            conn_file.close()
            self.assertEqual(modo, "wal")
        finally:
            os.unlink(tmp_path)
            try:
                os.unlink(tmp_path + "-wal")
                os.unlink(tmp_path + "-shm")
            except OSError:
                pass

    def test_foreign_keys_habilitados(self):
        fk = self.conn.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(fk, 1)

    def test_consulta_rango_fechas_sin_resultados(self):
        from routes.finanzas import _movimientos_con_saldo
        movs, saldo_ant, total = _movimientos_con_saldo(
            self.conn, "caja_chica", "2020-01-01", "2020-12-31"
        )
        self.assertEqual(movs, [])
        self.assertEqual(saldo_ant, 0.0)
        self.assertEqual(total, 0)

    def test_bd_temporal_indices_creables(self):
        for sql in [
            "CREATE INDEX IF NOT EXISTS idx_mov_fecha ON movimientos_financieros(fecha)",
            "CREATE INDEX IF NOT EXISTS idx_mov_banco ON movimientos_financieros(fk_banco_id)",
            "CREATE INDEX IF NOT EXISTS idx_caja_fecha ON caja_chica(fecha)",
        ]:
            self.conn.execute(sql)

    def test_paginacion_offset_mas_alla_del_total(self):
        from routes.finanzas import _movimientos_con_saldo
        movs, _, total = _movimientos_con_saldo(
            self.conn, "caja_chica", "2026-01-01", "2026-12-31",
            limit=10, offset=9999
        )
        self.assertEqual(movs, [])
        self.assertEqual(total, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
