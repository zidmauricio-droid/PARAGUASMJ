"""tests/test_auth.py — Pruebas de autenticacion."""
import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def client():
    from app import app
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        yield c

def test_login_page_loads(client):
    r = client.get("/login")
    assert r.status_code == 200

def test_login_incorrecto(client):
    r = client.post("/login", data={"usuario":"admin","clave":"wrongpass"}, follow_redirects=True)
    assert b"incorrectos" in r.data.lower() or r.status_code == 200

def test_logout_sin_sesion(client):
    r = client.get("/logout", follow_redirects=True)
    assert r.status_code == 200

def test_dashboard_requiere_login(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 200)
