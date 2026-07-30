"""
tests/test_volumen_rc553.py — Tests de volumen y rendimiento RC5.5.3
Mide tiempos reales con datasets grandes: 10k docs, 50k audits, 1k expedientes.
Umbral aceptable: búsqueda < 2s, COUNT < 200ms.

Nota: los datasets de 100k/500k son para ejecución manual (pytest -m volumen_grande).
Los tests automáticos usan datasets reducidos para CI rápido.
"""
import sqlite3
import time
import tempfile
import os
import pytest


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db_volumen():
    """BD temporal con datos de volumen para todo el módulo."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA cache_size=-32000")  # 32MB cache

    # Esquema mínimo para tests de volumen
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS registro_central (
            pk_registro_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_completo  TEXT,
            tipo_documento   TEXT,
            asunto_resumen   TEXT,
            estado           TEXT DEFAULT 'Borrador',
            area             TEXT DEFAULT 'GA',
            fecha_radicacion TEXT,
            creado_por       TEXT DEFAULT 'test'
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_usuario TEXT,
            accion       TEXT,
            modulo       TEXT,
            descripcion  TEXT,
            timestamp    TEXT DEFAULT (datetime('now')),
            ip_address   TEXT DEFAULT '127.0.0.1'
        );
        CREATE TABLE IF NOT EXISTS expedientes (
            pk_expediente_id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo           TEXT,
            asunto           TEXT,
            estado           TEXT DEFAULT 'ABIERTO',
            fecha_apertura   TEXT
        );
        CREATE TABLE IF NOT EXISTS finanzas_caja (
            pk_mov_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha      TEXT,
            concepto   TEXT,
            tipo_mov   TEXT,
            importe    REAL,
            saldo      REAL
        );

        -- Índices equivalentes a los de producción
        CREATE INDEX IF NOT EXISTS idx_rc_estado ON registro_central(estado);
        CREATE INDEX IF NOT EXISTS idx_rc_area   ON registro_central(area);
        CREATE INDEX IF NOT EXISTS idx_rc_fecha_rad ON registro_central(fecha_radicacion DESC);
        CREATE INDEX IF NOT EXISTS idx_pqrs_estado ON audit_log(accion);
        CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(timestamp DESC);
    """)

    yield conn, db_path

    conn.close()
    os.unlink(db_path)


def _insertar_documentos(conn, cantidad: int):
    tipos = ["Resolución", "Acta", "Factura", "Oficio", "Contrato", "PQRS", "Informe"]
    estados = ["Borrador", "En_revision", "Aprobado", "Archivado"]
    areas   = ["GA", "GC", "GF", "GE", "GL"]
    conn.executemany(
        "INSERT INTO registro_central (codigo_completo, tipo_documento, asunto_resumen, estado, area, fecha_radicacion) VALUES (?,?,?,?,?,?)",
        [
            (f"RC-2026-{i:06d}",
             tipos[i % len(tipos)],
             f"Asunto de prueba número {i} para medir rendimiento del sistema",
             estados[i % len(estados)],
             areas[i % len(areas)],
             f"2026-{(i % 12)+1:02d}-{(i % 28)+1:02d}")
            for i in range(1, cantidad + 1)
        ]
    )
    conn.commit()


def _insertar_auditoria(conn, cantidad: int):
    acciones = ["LOGIN", "CREATE", "UPDATE", "DELETE", "VIEW", "EXPORT", "SLOW_ENDPOINT"]
    modulos  = ["documentos", "pqrs", "finanzas", "expedientes", "proyectos"]
    conn.executemany(
        "INSERT INTO audit_log (nombre_usuario, accion, modulo, descripcion, timestamp) VALUES (?,?,?,?,?)",
        [
            (f"usuario_{i % 10}",
             acciones[i % len(acciones)],
             modulos[i % len(modulos)],
             f"Evento de auditoría número {i}",
             f"2026-{(i % 12)+1:02d}-{(i % 28)+1:02d} {i % 24:02d}:{i % 60:02d}:00")
            for i in range(1, cantidad + 1)
        ]
    )
    conn.commit()


def _insertar_expedientes(conn, cantidad: int):
    estados = ["ABIERTO", "CERRADO", "ARCHIVADO"]
    conn.executemany(
        "INSERT INTO expedientes (codigo, asunto, estado, fecha_apertura) VALUES (?,?,?,?)",
        [
            (f"EXP-2026-{i:05d}",
             f"Expediente de prueba {i}",
             estados[i % len(estados)],
             f"2026-{(i % 12)+1:02d}-{(i % 28)+1:02d}")
            for i in range(1, cantidad + 1)
        ]
    )
    conn.commit()


def _insertar_finanzas(conn, cantidad: int):
    saldo = 0.0
    rows = []
    for i in range(1, cantidad + 1):
        importe = 50000 + (i % 500) * 1000
        tipo = "INGRESO" if i % 3 != 0 else "EGRESO"
        saldo = saldo + importe if tipo == "INGRESO" else saldo - importe
        rows.append((f"2026-{(i % 12)+1:02d}-{(i % 28)+1:02d}",
                      f"Movimiento {i}", tipo, importe, saldo))
    conn.executemany(
        "INSERT INTO finanzas_caja (fecha, concepto, tipo_mov, importe, saldo) VALUES (?,?,?,?,?)",
        rows
    )
    conn.commit()


# ── Tests de inserción masiva ─────────────────────────────────────────────────

class TestInsercionMasiva:
    """Verifica que las inserciones masivas completan en tiempo razonable."""

    def test_insertar_10k_documentos(self, db_volumen):
        conn, _ = db_volumen
        t0 = time.perf_counter()
        _insertar_documentos(conn, 10_000)
        elapsed = time.perf_counter() - t0
        total = conn.execute("SELECT COUNT(*) FROM registro_central").fetchone()[0]
        assert total >= 10_000, f"Solo {total} documentos insertados"
        assert elapsed < 10.0, f"Inserción tardó {elapsed:.2f}s (máx 10s)"

    def test_insertar_50k_auditoria(self, db_volumen):
        conn, _ = db_volumen
        t0 = time.perf_counter()
        _insertar_auditoria(conn, 50_000)
        elapsed = time.perf_counter() - t0
        total = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        assert total >= 50_000
        assert elapsed < 15.0, f"Auditoría tardó {elapsed:.2f}s (máx 15s)"

    def test_insertar_1k_expedientes(self, db_volumen):
        conn, _ = db_volumen
        t0 = time.perf_counter()
        _insertar_expedientes(conn, 1_000)
        elapsed = time.perf_counter() - t0
        total = conn.execute("SELECT COUNT(*) FROM expedientes").fetchone()[0]
        assert total >= 1_000
        assert elapsed < 5.0, f"Expedientes tardaron {elapsed:.2f}s (máx 5s)"

    def test_insertar_5k_movimientos(self, db_volumen):
        conn, _ = db_volumen
        t0 = time.perf_counter()
        _insertar_finanzas(conn, 5_000)
        elapsed = time.perf_counter() - t0
        total = conn.execute("SELECT COUNT(*) FROM finanzas_caja").fetchone()[0]
        assert total >= 5_000
        assert elapsed < 5.0, f"Finanzas tardaron {elapsed:.2f}s (máx 5s)"


# ── Tests de búsqueda con volumen ─────────────────────────────────────────────

class TestRendimientoBusqueda:
    """Verifica tiempos de consulta con datasets grandes."""

    def test_count_documentos_rapido(self, db_volumen):
        conn, _ = db_volumen
        t0 = time.perf_counter()
        n = conn.execute("SELECT COUNT(*) FROM registro_central WHERE estado='Borrador'").fetchone()[0]
        ms = (time.perf_counter() - t0) * 1000
        assert ms < 200, f"COUNT tardó {ms:.1f}ms (máx 200ms)"

    def test_busqueda_por_estado(self, db_volumen):
        conn, _ = db_volumen
        t0 = time.perf_counter()
        rows = conn.execute(
            "SELECT pk_registro_id, codigo_completo, asunto_resumen FROM registro_central WHERE estado=? ORDER BY pk_registro_id DESC LIMIT 20",
            ("Aprobado",)
        ).fetchall()
        ms = (time.perf_counter() - t0) * 1000
        assert len(rows) <= 20
        assert ms < 200, f"Búsqueda por estado tardó {ms:.1f}ms (máx 200ms)"

    def test_busqueda_texto_asunto(self, db_volumen):
        conn, _ = db_volumen
        t0 = time.perf_counter()
        rows = conn.execute(
            "SELECT pk_registro_id FROM registro_central WHERE asunto_resumen LIKE ? LIMIT 20",
            ("%número 5000%",)
        ).fetchall()
        ms = (time.perf_counter() - t0) * 1000
        assert ms < 2000, f"LIKE en asunto tardó {ms:.1f}ms (máx 2000ms)"

    def test_count_audit_semana(self, db_volumen):
        conn, _ = db_volumen
        t0 = time.perf_counter()
        n = conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE timestamp >= date('now','-7 days')"
        ).fetchone()[0]
        ms = (time.perf_counter() - t0) * 1000
        assert ms < 500, f"COUNT auditoría 7 días tardó {ms:.1f}ms (máx 500ms)"

    def test_paginacion_documentos(self, db_volumen):
        conn, _ = db_volumen
        t0 = time.perf_counter()
        rows = conn.execute(
            "SELECT * FROM registro_central ORDER BY pk_registro_id DESC LIMIT 20 OFFSET 5000"
        ).fetchall()
        ms = (time.perf_counter() - t0) * 1000
        assert len(rows) == 20
        assert ms < 500, f"Paginación OFFSET 5000 tardó {ms:.1f}ms (máx 500ms)"

    def test_expedientes_abiertos(self, db_volumen):
        conn, _ = db_volumen
        t0 = time.perf_counter()
        n = conn.execute(
            "SELECT COUNT(*) FROM expedientes WHERE estado='ABIERTO'"
        ).fetchone()[0]
        ms = (time.perf_counter() - t0) * 1000
        assert ms < 200, f"COUNT expedientes tardó {ms:.1f}ms (máx 200ms)"


# ── Tests del módulo de diagnóstico ──────────────────────────────────────────

class TestSystemDiagnostics:
    """Verifica el módulo core/system_diagnostics.py."""

    def test_ram_mb_retorna_valor(self):
        from core.system_diagnostics import _ram_mb
        ram = _ram_mb()
        # -1 si no se pudo leer (Windows sin ctypes, etc.)
        assert isinstance(ram, float)

    def test_diagnostico_completo_con_bd(self, db_volumen):
        from core.system_diagnostics import obtener_diagnostico_completo
        _, db_path = db_volumen
        diag = obtener_diagnostico_completo(db_path)
        assert "timestamp" in diag
        assert "ram_mb" in diag
        assert "db_tamano_mb" in diag
        assert "benchmarks" in diag
        assert isinstance(diag["tablas"], dict)

    def test_benchmarks_completan_en_tiempo(self, db_volumen):
        from core.system_diagnostics import _benchmark_consultas
        conn, _ = db_volumen
        t0 = time.perf_counter()
        benchmarks = _benchmark_consultas(conn)
        elapsed = time.perf_counter() - t0
        assert elapsed < 5.0, f"Benchmarks tardaron {elapsed:.2f}s"
        # Cada benchmark debe tener los campos esperados
        for b in benchmarks:
            assert "consulta" in b
            assert "ms" in b
            assert "nivel" in b

    def test_integridad_db(self, db_volumen):
        from core.system_diagnostics import _verificar_integridad
        conn, _ = db_volumen
        resultado = _verificar_integridad(conn)
        assert resultado == "ok", f"Integridad BD: {resultado}"

    def test_modo_wal(self, db_volumen):
        from core.system_diagnostics import _modo_wal
        conn, _ = db_volumen
        assert _modo_wal(conn) is True


# ── Tests del clasificador documental ────────────────────────────────────────

class TestClasificadorVolumen:
    """Verifica rendimiento del clasificador con muchas clasificaciones."""

    def test_clasificar_1000_documentos_rapido(self):
        from core.document_classifier import clasificar_documento
        tipos = ["Resolución", "Acta", "Factura", "Oficio", "PQRS"]
        asuntos = [
            "Factura de servicio de acueducto",
            "Petición de suscriptor por presión baja",
            "Contrato de obra hidráulica",
            "Informe de gestión operativa",
            "Acta de asamblea de usuarios",
        ]
        t0 = time.perf_counter()
        for i in range(1000):
            clf = clasificar_documento(
                tipos[i % len(tipos)],
                asuntos[i % len(asuntos)],
                "GA"
            )
            assert clf.serie_codigo in {"FIN", "PQRS", "LEG", "ADM", "GOB", "OPS", "SUB", "PRY", "OTR"}
        elapsed = time.perf_counter() - t0
        assert elapsed < 2.0, f"1000 clasificaciones tardaron {elapsed:.2f}s (máx 2s)"

    def test_cache_lru_funciona(self):
        from core.document_classifier import _determinar_serie_cached
        _determinar_serie_cached.cache_clear()
        _determinar_serie_cached("factura pago servicio")
        _determinar_serie_cached("factura pago servicio")  # hit
        info = _determinar_serie_cached.cache_info()
        assert info.hits >= 1, "La caché LRU no registró hits"


# ── Marcador para tests de volumen grande (ejecución manual) ─────────────────

@pytest.mark.volumen_grande
def test_100k_documentos_manual(db_volumen):
    """Solo ejecutar con: pytest -m volumen_grande tests/test_volumen_rc553.py"""
    conn, _ = db_volumen
    _insertar_documentos(conn, 90_000)  # ya hay 10k insertados
    total = conn.execute("SELECT COUNT(*) FROM registro_central").fetchone()[0]
    assert total >= 100_000
    t0 = time.perf_counter()
    conn.execute(
        "SELECT COUNT(*) FROM registro_central WHERE estado='Borrador'"
    ).fetchone()
    ms = (time.perf_counter() - t0) * 1000
    print(f"\n[100k docs] COUNT por estado: {ms:.1f}ms")
    assert ms < 1000
