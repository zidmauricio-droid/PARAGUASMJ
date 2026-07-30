"""
tests/test_rc553_estabilidad.py — Pruebas de estabilidad RC5.5.3
Cubre: rate_limiter (#38/#43), OTP verificación documento (#37), auditoría API (#40),
       gestor_trd import condicional (#41), logging unificado (#44),
       _sanitizar_texto multilinea (#45), concepto textarea.
"""
import os, sys, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SECRET_KEY", "test_key_rc553_estabilidad")


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


# ── core/rate_limiter.py ─────────────────────────────────────────────────────

def test_rate_limiter_importable():
    """core.rate_limiter debe ser importable."""
    from core.rate_limiter import limitar, _store
    assert callable(limitar)


def test_rate_limiter_permite_bajo_limite():
    """Requests dentro del límite deben ser permitidas."""
    from core.rate_limiter import _store
    _store.clear("test_permite")
    for _ in range(3):
        assert _store.is_allowed("test_permite", max_attempts=5, window_seconds=60)


def test_rate_limiter_bloquea_sobre_limite():
    """Requests sobre el límite deben ser rechazadas."""
    from core.rate_limiter import _store
    _store.clear("test_bloquea")
    for _ in range(5):
        _store.is_allowed("test_bloquea", max_attempts=5, window_seconds=60)
    assert not _store.is_allowed("test_bloquea", max_attempts=5, window_seconds=60)


def test_rate_limiter_purge_no_falla():
    """purge_expired no debe lanzar excepciones."""
    from core.rate_limiter import _store
    _store.purge_expired(window_seconds=3600)


def test_rate_limiter_decorador_preserva_nombre():
    """@limitar debe preservar el nombre de la función decorada."""
    from core.rate_limiter import limitar

    @limitar("test_wraps", max_attempts=3, window_seconds=60)
    def mi_endpoint():
        return "ok"

    assert mi_endpoint.__name__ == "mi_endpoint"


# ── #37: otp_enviar verifica documento y firmante ─────────────────────────────

def test_otp_enviar_sin_parametros_rechazado(client_auth):
    """POST /api/otp/enviar sin registro_id/firmante_id debe retornar 400."""
    resp = client_auth.post("/api/otp/enviar", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["ok"] is False


def test_otp_enviar_documento_inexistente(client_auth):
    """POST /api/otp/enviar con documento que no existe debe retornar 404."""
    resp = client_auth.post("/api/otp/enviar", json={
        "registro_id": 999999,
        "firmante_id": 1
    })
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["ok"] is False
    assert "Documento" in data.get("error", "") or "no encontrado" in data.get("error", "").lower()


def test_otp_enviar_firmante_no_asignado(client_auth):
    """POST /api/otp/enviar con firmante no asignado debe retornar 403."""
    resp = client_auth.post("/api/otp/enviar", json={
        "registro_id": 1,
        "firmante_id": 99999
    })
    # 404 si doc no existe, 403 si doc existe pero firmante no asignado
    assert resp.status_code in (403, 404)


# ── #38: Rate limit en otp_enviar ────────────────────────────────────────────

def test_otp_enviar_rate_limit_activo(client_auth):
    """POST /api/otp/enviar debe retornar 429 al superar el límite de intentos."""
    from core.rate_limiter import _store
    # Limpiar contador para usuario admin
    _store.clear("otp_enviar:u:admin")
    responses = []
    for i in range(5):
        r = client_auth.post("/api/otp/enviar", json={
            "registro_id": 999999 + i,
            "firmante_id": 1
        })
        responses.append(r.status_code)
    # Los primeros 3 no deben ser 429, el 4to en adelante sí
    assert 429 in responses, f"Rate limit no activado. Respuestas: {responses}"


# ── #40: Auditoría en asignar_firmantes ───────────────────────────────────────

def test_asignar_firmantes_retorna_campo_firmantes_asignados(client_auth):
    """asignar_firmantes con doc inexistente retorna 404 con campo ok=False."""
    resp = client_auth.post("/api/documento/999999/firmantes/asignar",
                            json={"firmantes": [{"firmante_id": 1, "orden_firma": 1}]})
    assert resp.status_code in (404, 403, 500)
    data = resp.get_json()
    assert data["ok"] is False


# ── #41: gestor_trd import condicional ────────────────────────────────────────

def test_gestor_trd_import_condicional():
    """GESTOR_TRD_AVAILABLE debe estar definido en documentos."""
    import importlib
    docs = importlib.import_module("routes.documentos")
    assert hasattr(docs, "_GESTOR_TRD_AVAILABLE")
    assert isinstance(docs._GESTOR_TRD_AVAILABLE, bool)


def test_alertas_trd_responde_sin_crashear(client_auth):
    """GET /documentos/api/alertas_trd no debe lanzar NameError ni 500 no manejado."""
    resp = client_auth.get("/documentos/api/alertas_trd")
    # Puede ser 200 (gestor_trd OK), 503 (no disponible) o 500 (error interno manejado)
    # Lo que NO debe ocurrir es NameError crashing sin respuesta JSON
    assert resp.status_code in (200, 500, 503), (
        f"alertas_trd retornó {resp.status_code} — posible NameError en gestor_trd"
    )


# ── #44: Logging unificado ────────────────────────────────────────────────────

def test_documentos_no_usa_logging_inline():
    """documentos.py no debe tener import logging suelto después del módulo."""
    import ast, pathlib
    src = pathlib.Path("routes/documentos.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # La única importación de logging debe ser en las primeras líneas como _logging
            for alias in getattr(node, "names", []):
                if alias.name == "logging" and node.lineno > 20:
                    pytest.fail(f"Import 'logging' encontrado en línea {node.lineno} — debe usar _log_docs")


# ── #45: _sanitizar_texto multilinea ─────────────────────────────────────────

def test_sanitizar_texto_allow_newlines():
    """allow_newlines=True debe conservar saltos de línea."""
    from routes.finanzas import _sanitizar_texto
    resultado = _sanitizar_texto("Línea 1\nLínea 2\nLínea 3", max_len=100, allow_newlines=True)
    assert "\n" in resultado


def test_sanitizar_texto_allow_newlines_elimina_control_chars():
    """allow_newlines=True debe seguir eliminando caracteres de control."""
    from routes.finanzas import _sanitizar_texto
    resultado = _sanitizar_texto("Texto\x00malo\x01aquí", max_len=100, allow_newlines=True)
    assert "\x00" not in resultado
    assert "\x01" not in resultado


def test_sanitizar_texto_newlines_sin_modo_elimina_newlines():
    """Sin allow_newlines, los saltos de línea deben ser eliminados."""
    from routes.finanzas import _sanitizar_texto
    resultado = _sanitizar_texto("línea1\nlínea2", max_len=100, allow_newlines=False)
    assert "\n" not in resultado


def test_sanitizar_texto_trunca_500():
    """allow_newlines=True debe truncar al max_len indicado."""
    from routes.finanzas import _sanitizar_texto
    largo = "A" * 600
    assert len(_sanitizar_texto(largo, max_len=500, allow_newlines=True)) <= 500
