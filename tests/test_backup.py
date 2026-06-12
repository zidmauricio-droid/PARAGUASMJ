"""
tests/test_backup.py — Suite institucional RC5.5
Cobertura: crear backup, integrity_check, backup_test_restore, path traversal.
"""
import os
import sqlite3
import tempfile
import pytest
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def db_temporal():
    """BD temporal con tablas críticas para tests."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE usuarios (pk_usuario_id INTEGER PRIMARY KEY, nombre TEXT);
        CREATE TABLE registro_central (pk_registro_id INTEGER PRIMARY KEY, codigo TEXT);
        CREATE TABLE audit_log (id INTEGER PRIMARY KEY, accion TEXT, fecha TEXT);
        CREATE TABLE configuracion (clave TEXT PRIMARY KEY, valor TEXT);
        INSERT INTO usuarios VALUES (1, 'admin');
        INSERT INTO configuracion VALUES ('sistema', 'PARAGUASMJ');
    """)
    conn.commit(); conn.close()
    yield path
    os.unlink(path)


def test_backup_test_restore_ok(db_temporal):
    """Un backup bien formado debe pasar backup_test_restore."""
    from core.backup_manager import backup_test_restore
    resultado = backup_test_restore(db_temporal)
    assert resultado["ok"] is True
    assert len(resultado["tablas_verificadas"]) >= 2
    assert resultado["errores"] == []


def test_backup_test_restore_archivo_inexistente():
    """Archivo inexistente debe retornar ok=False."""
    from core.backup_manager import backup_test_restore
    resultado = backup_test_restore("/tmp/no_existe_nunca_123456.db")
    assert resultado["ok"] is False


def test_backup_path_traversal_rechazado():
    """Rutas fuera del BACKUP_FOLDER deben ser rechazadas."""
    from core.backup_manager import restaurar_backup
    resultado = restaurar_backup("/etc/passwd")
    assert resultado["success"] is False
    assert "fuera del directorio" in resultado["error"].lower() or "no encontrado" in resultado["error"].lower()


def test_crypto_es_cifrado_institucional_false():
    """es_cifrado_institucional() SIEMPRE debe retornar False."""
    from core.crypto_simple import es_cifrado_institucional
    assert es_cifrado_institucional() is False


def test_crypto_cifrar_descifrar_simetrico():
    """cifrar() y descifrar() deben ser inversos."""
    from core.crypto_simple import cifrar, descifrar
    original = "contrasena_smtp_secreta"
    cifrado = cifrar(original)
    assert cifrado != original
    assert cifrado.startswith("enc1:")
    assert descifrar(cifrado) == original


def test_crypto_descifrar_texto_plano_sin_prefijo():
    """descifrar() con texto sin prefijo 'enc1:' debe devolverlo intacto."""
    from core.crypto_simple import descifrar
    assert descifrar("texto_plano") == "texto_plano"
    assert descifrar("") == ""


def test_csrf_manager_token_no_vacio():
    """generar_token() debe retornar un string no vacío en contexto Flask."""
    import os
    os.environ.setdefault("SECRET_KEY", "test_key_para_tests_unitarios_sigca")
    from app import app
    with app.test_request_context():
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["usuario_id"] = 1
            from core.csrf_manager import generar_token
            with app.test_request_context():
                from flask import session
                session["usuario_id"] = 1
                token = generar_token()
                assert isinstance(token, str)
                assert len(token) == 64
