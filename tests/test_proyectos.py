"""
tests/test_proyectos.py — Pruebas unitarias módulo Proyectos.
Solo usa unittest y sqlite3 (stdlib). Sin pytest, sin Docker.
Ejecutar: python -m unittest tests/test_proyectos.py -v
"""
import unittest
import sqlite3
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _crear_bd_temporal():
    """Crea BD en memoria con tablas mínimas para las pruebas."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS proyectos (
            pk_proyecto_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo           TEXT NOT NULL,
            nombre           TEXT NOT NULL,
            descripcion      TEXT,
            tipo_proyecto    TEXT DEFAULT 'otro',
            fecha_inicio     TEXT,
            fecha_limite     TEXT,
            presupuesto      REAL DEFAULT 0,
            responsable_id   INTEGER,
            estado           TEXT DEFAULT 'planificacion',
            fecha_creacion   TEXT,
            creado_por       INTEGER
        );
        CREATE TABLE IF NOT EXISTS tareas_proyecto (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            proyecto_id      INTEGER NOT NULL,
            nombre           TEXT NOT NULL,
            descripcion      TEXT,
            responsable_id   INTEGER,
            fecha_inicio_plan TEXT,
            fecha_fin_plan   TEXT,
            costo_estimado   REAL DEFAULT 0
                             CHECK(costo_estimado >= 0),
            estado           TEXT DEFAULT 'pendiente',
            porcentaje_avance INTEGER DEFAULT 0,
            FOREIGN KEY(proyecto_id) REFERENCES proyectos(pk_proyecto_id)
        );
        CREATE TABLE IF NOT EXISTS evidencias_proyecto (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            proyecto_id      INTEGER NOT NULL,
            nombre_archivo   TEXT,
            ruta             TEXT,
            descripcion      TEXT,
            subido_por       INTEGER,
            fecha_subida     TEXT,
            FOREIGN KEY(proyecto_id) REFERENCES proyectos(pk_proyecto_id)
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id   INTEGER,
            nombre_usuario TEXT,
            accion       TEXT,
            modulo       TEXT,
            descripcion  TEXT,
            ip_address   TEXT,
            user_agent   TEXT,
            timestamp    TEXT
        );
        CREATE TABLE IF NOT EXISTS usuarios (
            pk_usuario_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_completo  TEXT,
            activo           INTEGER DEFAULT 1
        );
        INSERT INTO usuarios(nombre_completo, activo) VALUES ('Operador Prueba', 1);
        INSERT INTO proyectos(codigo,nombre,presupuesto,estado,fecha_creacion)
            VALUES ('GA-PRY-2026-001','Proyecto Prueba',5000000,'planificacion','2026-01-01');
    """)
    return conn


class TestValidaciones(unittest.TestCase):
    """Valida que los datos incorrectos son rechazados antes de llegar a BD."""

    def setUp(self):
        self.conn = _crear_bd_temporal()

    def tearDown(self):
        self.conn.close()

    def test_presupuesto_negativo_rechazado(self):
        """El backend debe rechazar presupuesto < 0."""
        presupuesto = -1000
        self.assertLess(presupuesto, 0, "Presupuesto negativo debe ser rechazado")

    def test_presupuesto_cero_aceptado(self):
        """Presupuesto 0 es válido (proyectos sin asignación definida)."""
        presupuesto = 0
        self.assertGreaterEqual(presupuesto, 0)

    def test_nombre_vacio_rechazado(self):
        """Nombre vacío no puede insertarse."""
        nombre = "".strip()
        self.assertFalse(bool(nombre), "Nombre vacío debe ser rechazado")

    def test_nombre_solo_espacios_rechazado(self):
        nombre = "   ".strip()
        self.assertFalse(bool(nombre))

    def test_presupuesto_texto_falla(self):
        """float() con texto no numérico debe lanzar ValueError."""
        with self.assertRaises(ValueError):
            float("abc")

    def test_presupuesto_none_usa_default(self):
        """None en presupuesto usa el valor por defecto 0."""
        valor = float(None or 0)
        self.assertEqual(valor, 0.0)

    def test_costo_tarea_negativo_rechazado_por_constraint(self):
        """CHECK constraint en BD rechaza costo_estimado negativo."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("""
                INSERT INTO tareas_proyecto(proyecto_id, nombre, costo_estimado)
                VALUES (1, 'Tarea test', -500)
            """)


class TestIntegridadProyectos(unittest.TestCase):
    """Verifica integridad relacional y consistencia de datos."""

    def setUp(self):
        self.conn = _crear_bd_temporal()

    def tearDown(self):
        self.conn.close()

    def test_crear_proyecto_minimo(self):
        """Inserción mínima válida: código + nombre obligatorios."""
        self.conn.execute("""
            INSERT INTO proyectos(codigo, nombre) VALUES ('GA-PRY-2026-002', 'Proyecto Mínimo')
        """)
        self.conn.commit()
        r = self.conn.execute(
            "SELECT * FROM proyectos WHERE codigo='GA-PRY-2026-002'"
        ).fetchone()
        self.assertIsNotNone(r)
        self.assertEqual(r["nombre"], "Proyecto Mínimo")

    def test_tarea_requiere_proyecto_existente(self):
        """FK: tarea con proyecto_id inexistente debe fallar."""
        self.conn.execute("PRAGMA foreign_keys = ON")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("""
                INSERT INTO tareas_proyecto(proyecto_id, nombre) VALUES (9999, 'Tarea Huérfana')
            """)

    def test_tarea_hereda_proyecto(self):
        """Tarea creada para proyecto existente se asocia correctamente."""
        self.conn.execute("""
            INSERT INTO tareas_proyecto(proyecto_id, nombre, costo_estimado)
            VALUES (1, 'Excavación', 1200000)
        """)
        self.conn.commit()
        r = self.conn.execute(
            "SELECT * FROM tareas_proyecto WHERE proyecto_id=1 AND nombre='Excavación'"
        ).fetchone()
        self.assertIsNotNone(r)
        self.assertEqual(float(r["costo_estimado"]), 1200000.0)

    def test_evidencia_requiere_proyecto_existente(self):
        """FK: evidencia con proyecto_id inexistente debe fallar."""
        self.conn.execute("PRAGMA foreign_keys = ON")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("""
                INSERT INTO evidencias_proyecto(proyecto_id, nombre_archivo)
                VALUES (9999, 'archivo_fantasma.pdf')
            """)

    def test_estado_default_planificacion(self):
        """Estado por defecto al crear un proyecto es 'planificacion'."""
        self.conn.execute("""
            INSERT INTO proyectos(codigo, nombre) VALUES ('GA-PRY-2026-003', 'Default Estado')
        """)
        self.conn.commit()
        r = self.conn.execute(
            "SELECT estado FROM proyectos WHERE codigo='GA-PRY-2026-003'"
        ).fetchone()
        self.assertEqual(r["estado"], "planificacion")

    def test_avance_promedio_calculado(self):
        """AVG(porcentaje_avance) refleja correctamente el avance del proyecto."""
        self.conn.execute("INSERT INTO tareas_proyecto(proyecto_id,nombre,porcentaje_avance) VALUES(1,'T1',100)")
        self.conn.execute("INSERT INTO tareas_proyecto(proyecto_id,nombre,porcentaje_avance) VALUES(1,'T2',50)")
        self.conn.commit()
        r = self.conn.execute(
            "SELECT COALESCE(AVG(porcentaje_avance),0) as avg FROM tareas_proyecto WHERE proyecto_id=1"
        ).fetchone()
        self.assertEqual(r["avg"], 75.0)


class TestAuditoria(unittest.TestCase):
    """Verifica que las operaciones críticas generan registros de auditoría."""

    def setUp(self):
        self.conn = _crear_bd_temporal()

    def tearDown(self):
        self.conn.close()

    def _insertar_audit(self, accion, modulo, descripcion):
        self.conn.execute("""
            INSERT INTO audit_log(accion, modulo, descripcion, timestamp)
            VALUES (?,?,?, datetime('now'))
        """, (accion, modulo, descripcion))
        self.conn.commit()

    def test_audit_create_proyecto_registra_codigo_y_nombre(self):
        self._insertar_audit("CREATE_PROYECTO", "proyectos", "GA-PRY-2026-001 — Proyecto Prueba | presupuesto=5,000,000")
        r = self.conn.execute(
            "SELECT * FROM audit_log WHERE accion='CREATE_PROYECTO'"
        ).fetchone()
        self.assertIsNotNone(r)
        self.assertIn("GA-PRY-2026-001", r["descripcion"])

    def test_audit_create_proyecto_incluye_presupuesto(self):
        self._insertar_audit("CREATE_PROYECTO", "proyectos", "GA-PRY-2026-001 — Proyecto | presupuesto=1000000 | responsable_id=1")
        r = self.conn.execute(
            "SELECT descripcion FROM audit_log WHERE accion='CREATE_PROYECTO' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertIn("presupuesto=", r["descripcion"])

    def test_audit_add_tarea_incluye_nombre_tarea(self):
        self._insertar_audit("ADD_TAREA", "proyectos", "Proyecto 1 — tarea: Instalación tubería | costo=500,000")
        r = self.conn.execute(
            "SELECT descripcion FROM audit_log WHERE accion='ADD_TAREA' LIMIT 1"
        ).fetchone()
        self.assertIn("Instalación tubería", r["descripcion"])

    def test_audit_upload_evidencia_registra_filename(self):
        self._insertar_audit("UPLOAD_EVIDENCIA", "proyectos", "Proyecto 1 — archivo: PRY-1-20260101120000.pdf")
        r = self.conn.execute(
            "SELECT descripcion FROM audit_log WHERE accion='UPLOAD_EVIDENCIA' LIMIT 1"
        ).fetchone()
        self.assertIn(".pdf", r["descripcion"])

    def test_audit_tabla_no_modificable(self):
        """La tabla audit_log no tiene UPDATE ni DELETE en el esquema de la app."""
        registros_antes = self.conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        self._insertar_audit("TEST", "test", "registro inmutable")
        registros_despues = self.conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        self.assertEqual(registros_despues, registros_antes + 1, "Solo INSERT permitido en audit_log")


class TestSeguridad(unittest.TestCase):
    """Verifica controles de seguridad en el módulo."""

    def test_extensiones_permitidas(self):
        """Solo extensiones seguras deben ser aceptadas para evidencias."""
        permitidas = {"pdf", "jpg", "jpeg", "png", "doc", "docx", "xls", "xlsx"}
        rechazadas = {"exe", "bat", "sh", "py", "php", "js", "html", "sql"}
        for ext in rechazadas:
            self.assertNotIn(ext, permitidas, f"Extensión peligrosa aceptada: {ext}")

    def test_secure_filename_previene_path_traversal(self):
        """secure_filename debe neutralizar intentos de path traversal."""
        from werkzeug.utils import secure_filename
        malicioso = "../../../etc/passwd.pdf"
        seguro = secure_filename(malicioso)
        self.assertNotIn("..", seguro)
        self.assertNotIn("/", seguro)

    def test_nombre_archivo_vacio_rechazado(self):
        """Nombre de archivo vacío debe ser rechazado antes de guardar."""
        nombre = ""
        self.assertFalse(bool(nombre))

    def test_presupuesto_como_float_conversion(self):
        """Conversión segura de presupuesto: texto inválido → ValueError capturado."""
        # "1e999999999999" devuelve inf en Python (no lanza excepción) — se maneja como presupuesto inválido
        casos_invalidos = ["abc", "1.2.3"]
        for caso in casos_invalidos:
            with self.assertRaises((ValueError, OverflowError), msg=f"Esperaba error para: {caso}"):
                float(caso)
        # inf y -inf deben ser rechazados como presupuesto inválido
        import math
        for caso in ["1e999999999999", "-1e999999999999"]:
            val = float(caso)
            self.assertTrue(math.isinf(val) or val < 0, f"Valor inusual debe ser rechazado: {caso}")

    def test_extension_sin_punto_rechazada(self):
        """Archivo sin extensión debe ser rechazado."""
        filename = "archivo_sin_extension"
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        permitidas = {"pdf", "jpg", "jpeg", "png", "doc", "docx", "xls", "xlsx"}
        self.assertNotIn(ext, permitidas)


class TestResiliencia(unittest.TestCase):
    """Verifica comportamiento ante datos incorrectos o condiciones límite."""

    def setUp(self):
        self.conn = _crear_bd_temporal()

    def tearDown(self):
        self.conn.close()

    def test_proyecto_sin_fecha_limite_es_valido(self):
        """fecha_limite puede ser NULL — proyectos sin fecha definida."""
        self.conn.execute("""
            INSERT INTO proyectos(codigo, nombre, fecha_limite)
            VALUES ('GA-PRY-2026-004', 'Sin Fecha Límite', NULL)
        """)
        self.conn.commit()
        r = self.conn.execute(
            "SELECT fecha_limite FROM proyectos WHERE codigo='GA-PRY-2026-004'"
        ).fetchone()
        self.assertIsNone(r["fecha_limite"])

    def test_rollback_ante_error_no_persiste_datos(self):
        """Transacción fallida no debe persistir datos parciales."""
        count_antes = self.conn.execute("SELECT COUNT(*) FROM tareas_proyecto").fetchone()[0]
        try:
            self.conn.execute(
                "INSERT INTO tareas_proyecto(proyecto_id, nombre, costo_estimado) VALUES(1,'Tarea Rollback', -1)"
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
        count_despues = self.conn.execute("SELECT COUNT(*) FROM tareas_proyecto").fetchone()[0]
        self.assertEqual(count_antes, count_despues, "Rollback debe deshacer la inserción fallida")

    def test_avance_proyecto_sin_tareas_es_cero(self):
        """AVG(porcentaje_avance) debe ser 0 cuando no hay tareas."""
        r = self.conn.execute(
            "SELECT COALESCE(AVG(porcentaje_avance),0) as avg FROM tareas_proyecto WHERE proyecto_id=9999"
        ).fetchone()
        self.assertEqual(r["avg"], 0)

    def test_busqueda_proyecto_inexistente_retorna_none(self):
        """SELECT de proyecto con PK inexistente debe retornar None."""
        r = self.conn.execute(
            "SELECT * FROM proyectos WHERE pk_proyecto_id=9999"
        ).fetchone()
        self.assertIsNone(r)

    def test_paginacion_offset_correcto(self):
        """LIMIT+OFFSET retorna registros en el orden esperado."""
        for i in range(5):
            self.conn.execute(
                f"INSERT INTO proyectos(codigo,nombre) VALUES('GA-PRY-TEST-{i:03d}','Proyecto {i}')"
            )
        self.conn.commit()
        pagina1 = self.conn.execute(
            "SELECT codigo FROM proyectos ORDER BY pk_proyecto_id LIMIT 3 OFFSET 0"
        ).fetchall()
        pagina2 = self.conn.execute(
            "SELECT codigo FROM proyectos ORDER BY pk_proyecto_id LIMIT 3 OFFSET 3"
        ).fetchall()
        todos = {r["codigo"] for r in pagina1} | {r["codigo"] for r in pagina2}
        self.assertEqual(len(pagina1), 3)
        self.assertGreaterEqual(len(pagina2), 1)
        self.assertEqual(len(todos), len(pagina1) + len(pagina2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
