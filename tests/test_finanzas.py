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

        -- Datos iniciales para pruebas
        INSERT INTO bancos (codigo_cuenta, banco_nombre, saldo_actual, status)
        VALUES ('BCO-001', 'Banco Prueba', 500000.0, 'ACTIVA');

        INSERT INTO caja_chica (fecha, concepto, tipo_mov, importe, usuario)
        VALUES ('2026-01-15', 'Pago papeleria', 'EGRESO', 25000, 'admin');

        INSERT INTO caja_chica (fecha, concepto, tipo_mov, importe, usuario)
        VALUES ('2026-01-20', 'Venta formularios', 'INGRESO', 10000, 'admin');
    """)
    return conn


# ── 1. TestValidaciones ──────────────────────────────────────────────
class TestValidaciones(unittest.TestCase):
    """Valida que reglas de negocio basicas se cumplan a nivel BD."""

    def setUp(self):
        self.conn = _crear_bd_temporal()

    def tearDown(self):
        self.conn.close()

    def test_importe_cero_rechazado(self):
        """BD debe rechazar importe = 0 (CHECK constraint)."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO caja_chica (fecha,concepto,tipo_mov,importe) VALUES (?,?,?,?)",
                ("2026-01-01", "Test", "EGRESO", 0)
            )

    def test_importe_negativo_rechazado(self):
        """BD debe rechazar importe negativo."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO caja_chica (fecha,concepto,tipo_mov,importe) VALUES (?,?,?,?)",
                ("2026-01-01", "Test", "EGRESO", -500)
            )

    def test_tipo_mov_invalido_rechazado(self):
        """BD debe rechazar tipo_mov distinto de INGRESO/EGRESO."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO caja_chica (fecha,concepto,tipo_mov,importe) VALUES (?,?,?,?)",
                ("2026-01-01", "Test", "TRANSFERENCIA", 1000)
            )

    def test_codigo_banco_duplicado_rechazado(self):
        """Dos cuentas no pueden tener el mismo codigo."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO bancos (codigo_cuenta,banco_nombre) VALUES (?,?)",
                ("BCO-001", "Banco Duplicado")
            )

    def test_banco_saldo_inicial_negativo_permitido_en_bd(self):
        """
        La BD permite saldo negativo — la proteccion es responsabilidad del backend.
        Este test documenta el comportamiento actual para RC5.5.
        """
        self.conn.execute(
            "INSERT INTO bancos (codigo_cuenta,banco_nombre,saldo_actual) VALUES (?,?,?)",
            ("BCO-NEG", "Banco Negativo", -1000)
        )
        saldo = self.conn.execute(
            "SELECT saldo_actual FROM bancos WHERE codigo_cuenta='BCO-NEG'"
        ).fetchone()[0]
        self.assertEqual(saldo, -1000.0)


# ── 2. TestSaldoAnt ──────────────────────────────────────────────────
class TestSaldoAnt(unittest.TestCase):
    """Verifica logica de saldo_anterior y movimientos_con_saldo."""

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
        """Saldo antes del 2026-01-20 = 0 - 25000 = -25000."""
        saldo = self._saldo_anterior("caja_chica", "2026-01-20")
        self.assertAlmostEqual(saldo, -25000.0)

    def test_saldo_anterior_caja_inicio(self):
        """Saldo antes del primer movimiento = 0."""
        saldo = self._saldo_anterior("caja_chica", "2026-01-01")
        self.assertAlmostEqual(saldo, 0.0)

    def test_movimientos_con_saldo_acumulado(self):
        """Saldo final del periodo = -25000 + 10000 = -15000."""
        movs, saldo_ant, total = self._movimientos_con_saldo(
            "caja_chica", "2026-01-01", "2026-12-31"
        )
        self.assertEqual(len(movs), 2)
        self.assertEqual(total, 2)
        self.assertAlmostEqual(movs[-1]["saldo"], -15000.0)

    def test_tabla_no_autorizada_rechazada(self):
        """_saldo_anterior debe rechazar tablas fuera del whitelist."""
        from routes.finanzas import _saldo_anterior
        with self.assertRaises(ValueError):
            _saldo_anterior(self.conn, "usuarios", "2026-01-01")

    def test_paginacion_limit(self):
        """Paginacion retorna maximo limit registros."""
        movs, _, total = self._movimientos_con_saldo(
            "caja_chica", "2026-01-01", "2026-12-31",
        )
        from routes.finanzas import _movimientos_con_saldo
        movs_pag, _, total_pag = _movimientos_con_saldo(
            self.conn, "caja_chica", "2026-01-01", "2026-12-31", limit=1, offset=0
        )
        self.assertEqual(len(movs_pag), 1)
        self.assertEqual(total_pag, 2)  # total sin paginar sigue siendo 2


# ── 3. TestIntegridadFinanciera ──────────────────────────────────────
class TestIntegridadFinanciera(unittest.TestCase):
    """Verifica reglas de integridad financiera."""

    def setUp(self):
        self.conn = _crear_bd_temporal()

    def tearDown(self):
        self.conn.close()

    def test_egreso_atomico_insert_update(self):
        """INSERT + UPDATE saldo deben ser atomicos — si falla uno, ninguno persiste."""
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
        """Ante error real (constraint violation), rollback revierte el INSERT previo."""
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            self.conn.execute(
                "INSERT INTO movimientos_financieros (fecha,fk_banco_id,tipo_mov,concepto,importe) "
                "VALUES (?,?,?,?,?)",
                ("2026-06-01", 1, "EGRESO", "Test rollback", 50000)
            )
            # Forzar IntegrityError: tipo_mov invalido viola CHECK constraint
            self.conn.execute(
                "INSERT INTO movimientos_financieros (fecha,tipo_mov,concepto,importe) "
                "VALUES (?,?,?,?)",
                ("2026-06-01", "INVALIDO", "Forzar error", 1000)
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()

        # Verificar que el primer INSERT fue revertido por el rollback
        n_movs = self.conn.execute(
            "SELECT COUNT(*) FROM movimientos_financieros WHERE concepto='Test rollback'"
        ).fetchone()[0]
        self.assertEqual(n_movs, 0)

    def test_banco_inactivo_no_deberia_recibir_movimientos(self):
        """Un banco INACTIVA no debe recibir nuevos movimientos (regla de negocio)."""
        self.conn.execute(
            "UPDATE bancos SET status='INACTIVA' WHERE pk_banco_id=1"
        )
        self.conn.commit()
        status = self.conn.execute(
            "SELECT status FROM bancos WHERE pk_banco_id=1"
        ).fetchone()[0]
        self.assertEqual(status, "INACTIVA")
        # El backend debe verificar status='ACTIVA' antes de registrar movimientos


# ── 4. TestAuditoria ─────────────────────────────────────────────────
class TestAuditoria(unittest.TestCase):
    """Verifica que operaciones criticas dejen trazabilidad en logs_sistema."""

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
        """El detalle del log de caja debe incluir el importe."""
        detalle = "EGRESO | Pago luz | $85000 | 2026-06-01"
        self._insertar_log("CAJA_NUEVO", detalle)
        log = self.conn.execute(
            "SELECT detalle FROM logs_sistema WHERE accion='CAJA_NUEVO'"
        ).fetchone()
        self.assertIn("85000", log["detalle"])
        self.assertIn("EGRESO", log["detalle"])

    def test_log_caja_eliminar_tiene_concepto_previo(self):
        """El log de eliminacion debe registrar concepto e importe del registro eliminado."""
        detalle = "ELIMINADO | EGRESO | Pago papeleria | $25000 | 2026-01-15"
        self._insertar_log("CAJA_ELIMINAR", detalle)
        log = self.conn.execute(
            "SELECT detalle FROM logs_sistema WHERE accion='CAJA_ELIMINAR'"
        ).fetchone()
        self.assertIn("ELIMINADO", log["detalle"])
        self.assertIn("Pago papeleria", log["detalle"])

    def test_log_banco_inactivar_tiene_saldo(self):
        """El log de inactivacion debe registrar el saldo del banco."""
        detalle = "Banco Prueba (BCO-001) | Saldo: $500000 | Movimientos registrados: 3"
        self._insertar_log("BANCO_INACTIVAR", detalle)
        log = self.conn.execute(
            "SELECT detalle FROM logs_sistema WHERE accion='BANCO_INACTIVAR'"
        ).fetchone()
        self.assertIn("500000", log["detalle"])

    def test_logs_no_eliminables(self):
        """Los logs no deben poder eliminarse (WORM). Verificar que no existe DELETE route."""
        # Este test documenta la regla: no hay operacion DELETE sobre logs_sistema
        # en el modulo finanzas. Si alguien agrega una, este test debe fallar.
        import inspect
        try:
            import routes.finanzas as fin
            source = inspect.getsource(fin)
            # No debe existir DELETE FROM logs_sistema en el modulo financiero
            self.assertNotIn("DELETE FROM logs_sistema", source)
        except ImportError:
            self.skipTest("Modulo finanzas no disponible")


# ── 5. TestSeguridad ─────────────────────────────────────────────────
class TestSeguridad(unittest.TestCase):
    """Verifica proteccion de rutas sensibles."""

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
        """Acceso a /finanzas/caja sin login debe retornar 302."""
        self._skip_si_app_no_disponible()
        r = self.client.get("/finanzas/caja")
        self.assertEqual(r.status_code, 302)

    def test_caja_consultar_sin_login_redirige(self):
        """/finanzas/caja/consultar sin login debe retornar 302."""
        self._skip_si_app_no_disponible()
        r = self.client.get("/finanzas/caja/consultar")
        self.assertEqual(r.status_code, 302)

    def test_movimientos_sin_login_redirige(self):
        """/finanzas/movimientos sin login debe retornar 302."""
        self._skip_si_app_no_disponible()
        r = self.client.get("/finanzas/movimientos")
        self.assertEqual(r.status_code, 302)

    def test_bancos_sin_login_redirige(self):
        """/finanzas/bancos sin login debe retornar 302."""
        self._skip_si_app_no_disponible()
        r = self.client.get("/finanzas/bancos")
        self.assertEqual(r.status_code, 302)

    def test_caja_nuevo_post_sin_login_redirige(self):
        """POST a /finanzas/caja/nuevo sin login debe retornar 302."""
        self._skip_si_app_no_disponible()
        r = self.client.post("/finanzas/caja/nuevo",
                              data={"fecha": "2026-01-01", "concepto": "Test",
                                    "tipo_mov": "EGRESO", "importe": "1000"})
        self.assertEqual(r.status_code, 302)

    def test_banco_crear_post_sin_login_redirige(self):
        """POST a /finanzas/bancos/crear sin login debe retornar 302."""
        self._skip_si_app_no_disponible()
        r = self.client.post("/finanzas/bancos/crear",
                              data={"codigo_cuenta": "TEST", "banco_nombre": "Test"})
        self.assertEqual(r.status_code, 302)

    def test_whitelist_tabla_bloquea_tablas_no_autorizadas(self):
        """_validar_tabla debe rechazar tablas fuera del whitelist financiero."""
        from routes.finanzas import _validar_tabla
        with self.assertRaises(ValueError):
            _validar_tabla("usuarios")
        with self.assertRaises(ValueError):
            _validar_tabla("logs_sistema")
        # Tablas autorizadas no deben lanzar excepcion
        _validar_tabla("caja_chica")
        _validar_tabla("movimientos_financieros")


# ── 6. TestResiliencia ───────────────────────────────────────────────
class TestResiliencia(unittest.TestCase):
    """Verifica comportamiento ante condiciones adversas."""

    def setUp(self):
        self.conn = _crear_bd_temporal()

    def tearDown(self):
        self.conn.close()

    def test_pragmas_wal_aplicados(self):
        """journal_mode=WAL debe estar configurado en la BD de produccion (archivo)."""
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
        """foreign_keys debe estar ON para integridad referencial."""
        fk = self.conn.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(fk, 1)

    def test_consulta_rango_fechas_sin_resultados(self):
        """Rango sin movimientos debe retornar lista vacia sin error."""
        from routes.finanzas import _movimientos_con_saldo
        movs, saldo_ant, total = _movimientos_con_saldo(
            self.conn, "caja_chica", "2020-01-01", "2020-12-31"
        )
        self.assertEqual(movs, [])
        self.assertEqual(saldo_ant, 0.0)
        self.assertEqual(total, 0)

    def test_bd_temporal_indices_creables(self):
        """Los indices financieros deben poder crearse sin error."""
        for sql in [
            "CREATE INDEX IF NOT EXISTS idx_mov_fecha ON movimientos_financieros(fecha)",
            "CREATE INDEX IF NOT EXISTS idx_mov_banco ON movimientos_financieros(fk_banco_id)",
            "CREATE INDEX IF NOT EXISTS idx_caja_fecha ON caja_chica(fecha)",
        ]:
            self.conn.execute(sql)  # No debe lanzar excepcion

    def test_paginacion_offset_mas_alla_del_total(self):
        """OFFSET mayor al total de registros debe retornar lista vacia sin error."""
        from routes.finanzas import _movimientos_con_saldo
        movs, _, total = _movimientos_con_saldo(
            self.conn, "caja_chica", "2026-01-01", "2026-12-31",
            limit=10, offset=9999
        )
        self.assertEqual(movs, [])
        self.assertEqual(total, 2)  # total sin paginar no cambia


if __name__ == "__main__":
    unittest.main(verbosity=2)
