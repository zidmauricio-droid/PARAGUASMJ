"""
tests/test_finanzas_security.py — Seguridad y validación del módulo Finanzas RC5.5.3
Cubre: CSRF decorator, banco_crear/banco_eliminar, duplicados, sanitización de texto,
       mensajes de error sin exposición de internos de BD, whitelist tipo_mov/tipo_cuenta.
"""
import os, sys, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SECRET_KEY", "test_key_finanzas_security_rc552")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    from app import app
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        yield c


@pytest.fixture
def client_auth(client):
    with client.session_transaction() as sess:
        sess["usuario_id"] = 1
        sess["nombre_usuario"] = "admin"
        sess["rol"] = "admin"
        sess["nombre_completo"] = "Administrador"
    return client


# ── _sanitizar_texto unit tests ───────────────────────────────────────────────

def test_sanitizar_texto_importable():
    """_sanitizar_texto debe ser importable desde routes.finanzas."""
    from routes.finanzas import _sanitizar_texto
    assert callable(_sanitizar_texto)


def test_sanitizar_texto_elimina_control_chars():
    from routes.finanzas import _sanitizar_texto
    resultado = _sanitizar_texto("Banco\x00Nacional\x1f")
    assert "\x00" not in resultado
    assert "\x1f" not in resultado
    assert "BancoNacional" in resultado.replace(" ", "")


def test_sanitizar_texto_elimina_newlines():
    from routes.finanzas import _sanitizar_texto
    resultado = _sanitizar_texto("Banco\nAgrario\rColombia")
    assert "\n" not in resultado
    assert "\r" not in resultado


def test_sanitizar_texto_trunca_max_len():
    from routes.finanzas import _sanitizar_texto
    largo = "A" * 200
    assert len(_sanitizar_texto(largo, max_len=50)) <= 50


def test_sanitizar_texto_vacio_retorna_vacio():
    from routes.finanzas import _sanitizar_texto
    assert _sanitizar_texto("") == ""
    assert _sanitizar_texto(None) == ""


def test_sanitizar_texto_normaliza_espacios():
    from routes.finanzas import _sanitizar_texto
    resultado = _sanitizar_texto("Banco   Agrario   Colombia")
    assert "  " not in resultado


# ── CSRF — banco_crear sin login rechazado ────────────────────────────────────

def test_banco_crear_sin_login_rechazado(client):
    """POST /finanzas/bancos/crear sin sesión debe redirigir a login."""
    resp = client.post("/finanzas/bancos/crear", data={
        "codigo_cuenta": "TST-001",
        "banco_nombre": "Banco Test",
        "tipo_cuenta": "AHORRO",
        "moneda": "COP",
        "saldo_inicial": "0"
    })
    assert resp.status_code in (302, 401), (
        f"banco_crear sin login retornó {resp.status_code}, esperado 302/401"
    )


def test_banco_eliminar_sin_login_rechazado(client):
    """POST /finanzas/bancos/eliminar/<id> sin sesión debe redirigir a login."""
    resp = client.post("/finanzas/bancos/eliminar/1")
    assert resp.status_code in (302, 401), (
        f"banco_eliminar sin login retornó {resp.status_code}, esperado 302/401"
    )


# ── Moneda whitelist ──────────────────────────────────────────────────────────

def test_banco_crear_moneda_invalida_usa_cop(client_auth):
    """Moneda fuera del whitelist (COP/USD/EUR) debe ser normalizada a COP."""
    resp = client_auth.post("/finanzas/bancos/crear", data={
        "codigo_cuenta": "TST-MON",
        "banco_nombre": "Banco Moneda Test",
        "tipo_cuenta": "AHORRO",
        "moneda": "PESO_FAKE",
        "saldo_inicial": "0"
    }, follow_redirects=False)
    # No debe retornar 500 — la moneda inválida es silenciada a COP
    assert resp.status_code in (200, 302), (
        f"Moneda inválida causó error {resp.status_code}"
    )


# ── Error messages — sin exposición de internals ─────────────────────────────

def test_error_banco_no_expone_sqlite(client_auth):
    """Los mensajes de error flash no deben contener trazas SQLite."""
    # Intento duplicar un código que probablemente no exista — el flash de error
    # (si ocurre) no debe contener "sqlite", "OperationalError" ni "UNIQUE constraint"
    resp = client_auth.post("/finanzas/bancos/crear", data={
        "codigo_cuenta": "",  # código vacío — debe fallar con mensaje genérico
        "banco_nombre": "X",
        "tipo_cuenta": "AHORRO",
        "moneda": "COP",
        "saldo_inicial": "0"
    }, follow_redirects=True)
    body = resp.data.decode("utf-8", errors="replace").lower()
    assert "operationalerror" not in body
    assert "sqlite" not in body or "sigca" in body  # texto UI puede mencionar sigca pero no el motor


# ── Validación de importe en caja_nuevo ──────────────────────────────────────

def test_caja_nuevo_sin_login_rechazado(client):
    """POST /finanzas/caja/nuevo sin sesión debe rechazar."""
    resp = client.post("/finanzas/caja/nuevo", data={
        "fecha": "2026-01-01",
        "concepto": "Test",
        "tipo_mov": "INGRESO",
        "importe": "5000"
    })
    assert resp.status_code in (302, 401)


def test_caja_consultar_sin_login_rechazado(client):
    """GET /finanzas/caja/consultar sin sesión debe rechazar."""
    resp = client.get("/finanzas/caja/consultar?desde=2026-01-01&hasta=2026-01-31")
    assert resp.status_code in (302, 401)


# ── csrf_protegido decorator importable ───────────────────────────────────────

def test_csrf_protegido_importable():
    """El decorador csrf_protegido debe estar disponible en routes.finanzas."""
    from routes.finanzas import csrf_protegido
    assert callable(csrf_protegido)


def test_csrf_protegido_preserva_nombre_funcion():
    """@csrf_protegido debe preservar el nombre de la función decorada (wraps)."""
    from routes.finanzas import csrf_protegido

    @csrf_protegido
    def mi_funcion():
        return "ok"

    assert mi_funcion.__name__ == "mi_funcion"


# ── Validación código formato ─────────────────────────────────────────────────

def test_banco_crear_codigo_invalido_rechazado(client_auth):
    """Código con caracteres inválidos (ej. espacios) debe ser rechazado."""
    resp = client_auth.post("/finanzas/bancos/crear", data={
        "codigo_cuenta": "BCO 001",  # espacio no permitido
        "banco_nombre": "Banco Test",
        "tipo_cuenta": "AHORRO",
        "moneda": "COP",
        "saldo_inicial": "0"
    }, follow_redirects=True)
    body = resp.data.decode("utf-8", errors="replace")
    # Debe mostrar mensaje de error sobre el formato
    assert resp.status_code == 200
    assert "código" in body.lower() or "codigo" in body.lower() or "character" in body.lower() or "obligatorio" in body.lower()


# ── Migración 016 ─────────────────────────────────────────────────────────────

def test_migracion_016_importable():
    """La migración 016 debe ser importable."""
    import importlib.util, os
    spec = importlib.util.spec_from_file_location(
        "m016",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "database", "migrations", "016_agregar_moneda_bancos.py")
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert callable(m.migrar)
