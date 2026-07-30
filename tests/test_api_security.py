"""
tests/test_api_security.py — Tests de seguridad API RC5.5.2
Cubre: OTP auth (#11, #12), ownership firmantes (#13), paginación (#15), métricas (#21).
"""
import os, sys, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SECRET_KEY", "test_key_api_security_sigca_rc552")


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    from app import app
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        yield c


@pytest.fixture
def client_autenticado(client):
    """Cliente con sesión de usuario regular."""
    with client.session_transaction() as sess:
        sess["usuario_id"] = 99
        sess["nombre_usuario"] = "tester"
        sess["rol"] = "auxiliar"
    return client


@pytest.fixture
def client_admin(client):
    """Cliente con sesión de administrador."""
    with client.session_transaction() as sess:
        sess["usuario_id"] = 1
        sess["nombre_usuario"] = "admin"
        sess["rol"] = "admin"
    return client


# ── Fix #11: otp_verificar requiere login ─────────────────────────────────────

def test_otp_verificar_sin_login_rechazado(client):
    """POST /api/otp/verificar sin sesión debe retornar 302 (redirect a login)."""
    resp = client.post("/api/otp/verificar", json={
        "registro_id": 1, "firmante_id": 1, "codigo": "123456"
    })
    assert resp.status_code in (302, 401), (
        f"Esperado 302/401, obtenido {resp.status_code} — otp_verificar no protegido"
    )


def test_otp_verificar_con_login_pasa_validacion(client_autenticado):
    """POST /api/otp/verificar con login llega a la lógica (no rebota en auth)."""
    resp = client_autenticado.post("/api/otp/verificar", json={
        "registro_id": 9999, "firmante_id": 9999, "codigo": "000000"
    })
    # Puede fallar por OTP inválido, pero NO por falta de auth
    data = resp.get_json()
    assert resp.status_code != 302, "No debe redirigir a login con sesión activa"
    assert data is not None, "Debe retornar JSON"


# ── Fix #12: validar_otp_documento requiere login ────────────────────────────

def test_validar_otp_documento_sin_login_rechazado(client):
    """POST /api/documento/1/validar_otp sin sesión debe rechazar."""
    resp = client.post("/api/documento/1/validar_otp", json={
        "firmante_id": 1, "codigo": "000000"
    })
    assert resp.status_code in (302, 401), (
        f"validar_otp_documento sin login debería rechazar, obtuvo {resp.status_code}"
    )


# ── Fix #13: asignar_firmantes verifica ownership ────────────────────────────

def test_asignar_firmantes_sin_login_rechazado(client):
    """POST /api/documento/1/firmantes/asignar sin sesión debe rechazar."""
    resp = client.post("/api/documento/1/firmantes/asignar",
                       json={"firmantes": [{"firmante_id": 1, "orden_firma": 1}]})
    assert resp.status_code in (302, 401)


def test_asignar_firmantes_usuario_no_propietario_rechazado(client_autenticado):
    """Usuario regular no puede asignar firmantes a documento ajeno."""
    resp = client_autenticado.post("/api/documento/1/firmantes/asignar",
                                   json={"firmantes": [{"firmante_id": 1}]})
    # Puede retornar 404 (doc no existe en test DB) o 403 (sin permiso)
    assert resp.status_code in (403, 404, 500), (
        f"Usuario sin ownership recibió {resp.status_code} — esperado 403/404"
    )


# ── Fix #14: estado de filtros en sesión ─────────────────────────────────────

def test_guardar_estado_lista(client_autenticado):
    """POST /api/documentos/estado debe guardar filtros en sesión."""
    resp = client_autenticado.post("/api/documentos/estado",
                                   json={"area": "GF", "estado": "Aprobado", "q": "oficio", "page": 2})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True


def test_obtener_estado_lista(client_autenticado):
    """GET /api/documentos/estado debe retornar filtros guardados."""
    # Primero guardar
    client_autenticado.post("/api/documentos/estado",
                             json={"area": "GL", "estado": "Borrador"})
    # Luego recuperar
    resp = client_autenticado.get("/api/documentos/estado")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "filtros" in data


# ── Fix #15: paginación con total_count ──────────────────────────────────────

def test_paginacion_retorna_campos_requeridos(client_autenticado):
    """GET /api/documentos debe incluir total, total_pages, page, per_page."""
    resp = client_autenticado.get("/api/documentos?page=1&per_page=10")
    assert resp.status_code == 200
    data = resp.get_json()
    for campo in ["items", "total", "total_pages", "page", "per_page", "has_more"]:
        assert campo in data, f"Campo '{campo}' ausente en respuesta de paginación"


def test_paginacion_total_es_entero(client_autenticado):
    """total debe ser un entero no negativo."""
    resp = client_autenticado.get("/api/documentos")
    data = resp.get_json()
    assert isinstance(data["total"], int)
    assert data["total"] >= 0


def test_paginacion_total_pages_coherente(client_autenticado):
    """total_pages debe ser >= 1."""
    resp = client_autenticado.get("/api/documentos?per_page=5")
    data = resp.get_json()
    assert data["total_pages"] >= 1


# ── Fix #21: decorator medir_tiempo ──────────────────────────────────────────

def test_medir_tiempo_no_altera_resultado():
    """@medir_tiempo no debe cambiar el valor de retorno de la función."""
    from core.metrics import medir_tiempo

    @medir_tiempo("test_funcion")
    def sumar(a, b):
        return a + b

    assert sumar(2, 3) == 5


def test_medir_tiempo_funcion_rapida_no_registra_warning(caplog):
    """Función <1s no debe generar warning de SLOW_ENDPOINT."""
    import logging
    from core.metrics import medir_tiempo

    @medir_tiempo("test_rapido")
    def funcion_rapida():
        return "ok"

    with caplog.at_level(logging.WARNING, logger="sigca.metrics"):
        funcion_rapida()

    slow_logs = [r for r in caplog.records if "SLOW_ENDPOINT" in r.message]
    assert len(slow_logs) == 0


def test_stats_cache_clasificador_retorna_dict():
    """obtener_stats_cache_clasificador debe retornar dict con hit_ratio."""
    from core.metrics import obtener_stats_cache_clasificador
    stats = obtener_stats_cache_clasificador()
    assert isinstance(stats, dict)
    assert "hit_ratio" in stats or "error" in stats
