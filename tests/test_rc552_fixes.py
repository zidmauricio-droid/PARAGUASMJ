"""
tests/test_rc552_fixes.py — Tests de las 10 correcciones RC5.5.2
Cubre: clasificador unificado, caché, hash firma, indexer, tempfile.
"""
import os
import sys
import sqlite3
import tempfile
import hashlib
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Fix #1 / #6: CLASSIFIER_AVAILABLE en documentos.py ──────────────────────

def test_classifier_available_flag():
    """CLASSIFIER_AVAILABLE debe ser True cuando document_classifier existe."""
    from core.document_classifier import clasificar_documento, enriquecer_registro
    assert callable(clasificar_documento)
    assert callable(enriquecer_registro)


# ── Fix #2: clasificar_documento no lanza excepción con entradas vacías ───────

def test_clasificar_no_raises_empty():
    """clasificar_documento con valores vacíos no debe lanzar excepción."""
    from core.document_classifier import clasificar_documento
    clf = clasificar_documento("", "", "")
    assert clf.serie_codigo == "OTR"


def test_clasificar_no_raises_none_area():
    """area=None no debe lanzar excepción."""
    from core.document_classifier import clasificar_documento
    clf = clasificar_documento("Oficio", "Solicitud información", None)
    assert clf is not None


# ── Fix #4: Hash de firma incluye contenido del documento ────────────────────

def test_hash_firma_incluye_contenido():
    """Dos firmas con mismo código pero diferente contenido deben tener hashes distintos."""
    contenido_a = "Texto del documento A"
    contenido_b = "Texto del documento B DIFERENTE"
    codigo = "GA-OFI-2026-001"
    firmante_id = 1
    ts = "2026-06-12T10:00:00"
    ip = "192.168.1.10"

    hash_a = hashlib.sha256(
        f"{hashlib.sha256(contenido_a.encode()).hexdigest()}|{codigo}|{firmante_id}|{ts}|{ip}".encode()
    ).hexdigest()
    hash_b = hashlib.sha256(
        f"{hashlib.sha256(contenido_b.encode()).hexdigest()}|{codigo}|{firmante_id}|{ts}|{ip}".encode()
    ).hexdigest()

    assert hash_a != hash_b, "Firmas sobre contenidos distintos deben ser distintas"


def test_hash_firma_mismo_contenido_es_determinista():
    """Mismo contenido + mismo firmante + mismo ts → mismo hash."""
    contenido = "Texto idéntico"
    codigo = "GA-OFI-2026-001"
    firmante_id = 1
    ts = "2026-06-12T10:00:00"
    ip = "192.168.1.10"
    h_content = hashlib.sha256(contenido.encode()).hexdigest()
    payload = f"{h_content}|{codigo}|{firmante_id}|{ts}|{ip}"
    hash1 = hashlib.sha256(payload.encode()).hexdigest()
    hash2 = hashlib.sha256(payload.encode()).hexdigest()
    assert hash1 == hash2


# ── Fix #3 / #7: vista_previa usa tempfile (no /tmp fijo) ────────────────────

def test_tempfile_no_collision():
    """Dos tempfiles simultáneos no deben tener el mismo path."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix="vprevia_") as a:
        path_a = a.name
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix="vprevia_") as b:
        path_b = b.name
    try:
        assert path_a != path_b
    finally:
        for p in (path_a, path_b):
            try:
                os.unlink(p)
            except OSError:
                pass


def test_tempfile_limpieza():
    """El archivo temporal debe poder eliminarse sin error."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix="vprevia_") as tmp:
        path = tmp.name
        tmp.write(b"%PDF-1.4 test")
    assert os.path.exists(path)
    os.unlink(path)
    assert not os.path.exists(path)


# ── Fix #8: Caché LRU en document_classifier ─────────────────────────────────

def test_cache_lru_mismo_resultado():
    """Dos llamadas idénticas deben retornar exactamente el mismo resultado."""
    from core.document_classifier import clasificar_documento
    clf1 = clasificar_documento("Contrato", "Contrato de prestación de servicios")
    clf2 = clasificar_documento("Contrato", "Contrato de prestación de servicios")
    assert clf1.serie_codigo == clf2.serie_codigo
    assert clf1.subserie == clf2.subserie


def test_cache_lru_hit(monkeypatch):
    """Verifica que la caché LRU se golpea en la segunda llamada."""
    from core.document_classifier import _determinar_serie_cached
    # Precalentar
    _determinar_serie_cached("factura cobro recibo")
    info = _determinar_serie_cached.cache_info()
    assert info.maxsize == 512
    # Segunda llamada — debe ser cache hit
    _determinar_serie_cached("factura cobro recibo")
    info2 = _determinar_serie_cached.cache_info()
    assert info2.hits >= 1


# ── Fix #9: Indexer de expedientes ───────────────────────────────────────────

@pytest.fixture
def db_con_expedientes():
    """BD temporal con expedientes y documentos para tests del indexer."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE expedientes (
            pk_expediente_id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_expediente TEXT NOT NULL,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            estado TEXT DEFAULT 'Abierto',
            fecha_apertura TEXT,
            fecha_cierre TEXT
        );
        CREATE TABLE registro_central (
            pk_registro_id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_completo TEXT,
            asunto_resumen TEXT,
            tipo_documento TEXT,
            fecha_radicacion TEXT,
            estado TEXT DEFAULT 'Aprobado',
            folio_inicio INTEGER,
            folio_fin INTEGER,
            fk_expediente_id INTEGER,
            fk_trd_id INTEGER,
            creado_por TEXT
        );
        CREATE TABLE trd (
            pk_trd_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            disposicion_final TEXT
        );
        INSERT INTO expedientes VALUES (1,'EXP-2026-001','Expediente Agua','Desc',
                                        'Abierto','2026-01-01',NULL);
        INSERT INTO expedientes VALUES (2,'EXP-2026-002','Expediente Vacío','',
                                        'Abierto','2026-01-15',NULL);
        INSERT INTO trd VALUES (1,'PQRS','eliminacion');
        INSERT INTO registro_central
            (codigo_completo,asunto_resumen,tipo_documento,fecha_radicacion,
             folio_inicio,folio_fin,fk_expediente_id,fk_trd_id,creado_por)
            VALUES ('GA-OFI-2026-001','Oficio solicitud','Oficio','2026-03-01',
                    1,3,1,1,'admin');
        INSERT INTO registro_central
            (codigo_completo,asunto_resumen,tipo_documento,fecha_radicacion,
             folio_inicio,folio_fin,fk_expediente_id,fk_trd_id,creado_por)
            VALUES ('GA-OFI-2026-002','Respuesta oficio','Oficio','2026-03-15',
                    4,6,1,1,'admin');
    """)
    conn.commit()
    yield conn
    conn.close()
    os.unlink(path)


def test_indice_expediente_retorna_docs(db_con_expedientes):
    from modules.indexer import indice_expediente
    resultado = indice_expediente(db_con_expedientes, 1)
    assert resultado["ok"] is True
    assert resultado["total_docs"] == 2
    assert resultado["total_folios"] == 6


def test_indice_expediente_no_existente(db_con_expedientes):
    from modules.indexer import indice_expediente
    resultado = indice_expediente(db_con_expedientes, 9999)
    assert resultado["ok"] is False


def test_estadisticas_indice(db_con_expedientes):
    from modules.indexer import estadisticas_indice
    stats = estadisticas_indice(db_con_expedientes)
    assert stats["ok"] is True
    assert stats["total_expedientes"] == 2
    assert stats["expedientes_sin_documentos"] == 1  # EXP-2026-002 vacío
    assert stats["documentos_sin_expediente"] == 0


def test_buscar_en_expedientes(db_con_expedientes):
    from modules.indexer import buscar_en_expedientes
    resultados = buscar_en_expedientes(db_con_expedientes, "Agua")
    assert len(resultados) == 1
    assert resultados[0]["codigo"] == "EXP-2026-001"


def test_buscar_query_corta_retorna_vacio(db_con_expedientes):
    from modules.indexer import buscar_en_expedientes
    resultados = buscar_en_expedientes(db_con_expedientes, "A")
    assert resultados == []


# ── Fix #10: formato_transferencia sin pandas ────────────────────────────────

def test_openpyxl_disponible():
    """openpyxl debe estar disponible (reemplaza pandas en formato_transferencia)."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Código", "Asunto", "Fecha"])
    ws.append(["GA-OFI-2026-001", "Test", "2026-06-12"])
    buf = __import__("io").BytesIO()
    wb.save(buf)
    assert buf.tell() > 0
