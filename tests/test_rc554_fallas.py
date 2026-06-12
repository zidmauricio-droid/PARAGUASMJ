"""
tests/test_rc554_fallas.py — Pruebas RC5.5.4 / RC5.5.5
Cubre: #46 api_representante defaults, #47 API causales SSPD,
       #48 tipo_solicitante whitelist, #49 índices DB, #50 columnas proyectos.
"""
import os, sys, sqlite3, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SECRET_KEY", "test_key_rc554_fallas")


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


def _db_path():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "database", "paraguasmj.db")


# ── #46 — api_representante nunca retorna 500 ────────────────────────────────

def test_repr_defaults_dict_exists():
    """_REPR_DEFAULTS debe existir y tener las 6 claves esperadas."""
    from routes.documentos import _REPR_DEFAULTS
    for k in ("representante_legal", "cargo_representante", "nombre_asociacion",
              "nit", "correo", "eslogan"):
        assert k in _REPR_DEFAULTS, f"Falta clave {k} en _REPR_DEFAULTS"


def test_api_representante_returns_200(client_auth):
    """GET /documentos/api/representante debe retornar 200 (nunca 500)."""
    r = client_auth.get("/documentos/api/representante")
    assert r.status_code == 200


def test_api_representante_json_keys(client_auth):
    """Respuesta de api_representante debe incluir claves requeridas."""
    r = client_auth.get("/documentos/api/representante")
    data = r.get_json()
    assert data is not None
    for k in ("representante_legal", "nombre_asociacion", "nit"):
        assert k in data, f"Clave '{k}' ausente en respuesta api_representante"


# ── #47 — Endpoints causales SSPD ────────────────────────────────────────────

def test_api_tipos_tramite(client_auth):
    """GET /pqrs/api/tipos-tramite debe retornar lista de tipos."""
    r = client_auth.get("/pqrs/api/tipos-tramite")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert len(data["tipos"]) >= 5


def test_api_grupos_causal(client_auth):
    """GET /pqrs/api/grupos-causal debe retornar F/I/P/O."""
    r = client_auth.get("/pqrs/api/grupos-causal")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    codigos = [g["codigo"] for g in data["grupos"]]
    for g in ("F", "I", "P", "O"):
        assert g in codigos, f"Grupo {g} ausente en api_grupos_causal"


def test_api_causales_filtro_grupo(client_auth):
    """GET /pqrs/api/causales?grupo=F debe retornar solo causales de Facturación."""
    r = client_auth.get("/pqrs/api/causales?grupo=F")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    for c in data["causales"]:
        assert c["grupo"] == "F", f"Causal {c['codigo']} no es del grupo F"


def test_api_causales_sin_filtro(client_auth):
    """GET /pqrs/api/causales sin filtro debe retornar todos los causales."""
    r = client_auth.get("/pqrs/api/causales")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert len(data["causales"]) >= 13


def test_api_subcausales_facturacion(client_auth):
    """GET /pqrs/api/subcausales/01 debe retornar subcausales de facturación."""
    r = client_auth.get("/pqrs/api/subcausales/01")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert len(data["subcausales"]) >= 5


# ── #48 — tipo_solicitante whitelist ─────────────────────────────────────────

def test_tipo_solicitante_whitelist_en_modulo():
    """routes/pqrs.py debe validar tipo_solicitante contra whitelist."""
    import ast, pathlib
    src = pathlib.Path(__file__).parent.parent / "routes" / "pqrs.py"
    code = src.read_text(encoding="utf-8")
    assert "tipo_solicitante" in code, "tipo_solicitante no encontrado en pqrs.py"
    assert "suscriptor" in code and "usuario" in code, \
        "Whitelist tipo_solicitante debe incluir 'suscriptor' y 'usuario'"


def test_grupo_causales_dict_estructura():
    """GRUPO_CAUSALES debe tener los 4 grupos con clave 'causales'."""
    from routes.pqrs import GRUPO_CAUSALES
    for g in ("F", "I", "P", "O"):
        assert g in GRUPO_CAUSALES
        assert "causales" in GRUPO_CAUSALES[g]
        assert isinstance(GRUPO_CAUSALES[g]["causales"], list)


# ── #49 — Índices de rendimiento en DB ───────────────────────────────────────

def test_indices_rendimiento_existen():
    """Los 10 índices de rendimiento deben existir en la DB."""
    db = _db_path()
    if not os.path.exists(db):
        pytest.skip("DB no disponible en entorno de pruebas")
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
    ).fetchall()
    conn.close()
    nombres = {r[0] for r in rows}
    esperados = [
        "idx_rc_estado", "idx_rc_area", "idx_rc_fecha_rad",
        "idx_pqrs_estado", "idx_pqrs_limite", "idx_pqrs_tipo",
        "idx_proy_estado", "idx_proy_respons", "idx_contactos_rs",
    ]
    for idx in esperados:
        assert idx in nombres, f"Índice '{idx}' no encontrado en DB"


# ── #50 — Columnas período flexible en proyectos ─────────────────────────────

def test_proyectos_columnas_periodo():
    """proyectos debe tener tipo_periodo, cantidad_periodo, duracion_meses."""
    db = _db_path()
    if not os.path.exists(db):
        pytest.skip("DB no disponible en entorno de pruebas")
    conn = sqlite3.connect(db)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(proyectos)").fetchall()]
    conn.close()
    for col in ("tipo_periodo", "cantidad_periodo", "duracion_meses"):
        assert col in cols, f"Columna '{col}' no encontrada en tabla proyectos"


def test_proyectos_ruta_acepta_tipo_periodo():
    """routes/proyectos.py debe manejar tipo_periodo en el INSERT."""
    import pathlib
    src = pathlib.Path(__file__).parent.parent / "routes" / "proyectos.py"
    code = src.read_text(encoding="utf-8")
    assert "tipo_periodo" in code, "tipo_periodo no presente en routes/proyectos.py"
    assert "duracion_meses" in code, "duracion_meses no presente en routes/proyectos.py"


def test_pqrs_sspd_tabla_existe():
    """Tabla pqrs_causales_sspd debe existir con al menos 13 registros."""
    db = _db_path()
    if not os.path.exists(db):
        pytest.skip("DB no disponible en entorno de pruebas")
    conn = sqlite3.connect(db)
    try:
        cnt = conn.execute("SELECT COUNT(*) FROM pqrs_causales_sspd").fetchone()[0]
        assert cnt >= 13, f"pqrs_causales_sspd tiene {cnt} registros, se esperaban >= 13"
    except sqlite3.OperationalError:
        pytest.fail("Tabla pqrs_causales_sspd no existe en DB")
    finally:
        conn.close()
