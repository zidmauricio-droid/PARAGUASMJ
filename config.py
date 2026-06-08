"""
config.py — PARAGUASMJ
Configuracion central. Compatible con Python directo y PyInstaller .exe.
"""
import os, sys, secrets

def resolver_ruta(rel):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.abspath("."), rel)

def definir_ruta_base_datos():
    base = os.path.dirname(sys.executable) if hasattr(sys,"frozen") else \
           os.path.join(os.path.dirname(os.path.abspath(__file__)), "database")
    os.makedirs(base, exist_ok=True)
    prop = os.path.join(base, "paraguasmj.db")
    try:
        t = os.path.join(base, ".test_write")
        open(t,"w").write("x"); os.remove(t)
        return prop
    except (IOError, OSError):
        fb = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "PARAGUASMJ")
        os.makedirs(fb, exist_ok=True)
        return os.path.join(fb, "paraguasmj.db")

def _cargar_o_crear_secret():
    """Persiste la SECRET_KEY en disco para sobrevivir reinicios del exe."""
    if "SECRET_KEY" in os.environ:
        return os.environ["SECRET_KEY"]
    base = os.path.dirname(sys.executable) if hasattr(sys, "frozen") else \
           os.path.dirname(os.path.abspath(__file__))
    ruta = os.path.join(base, ".app_secret")
    try:
        if os.path.isfile(ruta):
            clave = open(ruta).read().strip()
            if len(clave) == 64:
                return clave
        clave = secrets.token_hex(32)
        open(ruta, "w").write(clave)
        return clave
    except (IOError, OSError):
        return secrets.token_hex(32)

class Config:
    SECRET_KEY               = _cargar_o_crear_secret()
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = "Lax"
    PERMANENT_SESSION_LIFETIME = 28800
    DB_PATH                  = definir_ruta_base_datos()
    BASE_DIR                 = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER            = os.path.join(BASE_DIR, "uploads")
    PDF_FOLDER               = os.path.join(BASE_DIR, "pdfs")
    BACKUP_FOLDER            = os.path.join(BASE_DIR, "database", "backups")
    LOG_FOLDER               = os.path.join(BASE_DIR, "logs")
    NOMBRE_SISTEMA           = "PARAGUASMJ"
    NOMBRE_COMPLETO          = "Asociacion de Suscriptores del Acueducto Comunitario El Puente"
    NIT                      = "832.001.389-2"
    MUNICIPIO                = "Villeta, Cundinamarca"
    CORREO_OFICIAL           = "aacueductoelpuente@yahoo.com"
    REPRESENTANTE_LEGAL      = "Jose Humberto Ramirez"
    CARGO_REPRESENTANTE      = "Presidente"
    CODIGO_DIVIPOLA_DPTO     = "25"
    CODIGO_DIVIPOLA_MUN      = "258"
    DIAS_ALERTA_DOCUMENTOS   = 4
    DIAS_PLAZO_RESPUESTA     = 7
    DIAS_PLAZO_PQRS          = 15
    OTP_EXPIRA_MINUTOS       = 30
    BACKUPS_A_MANTENER       = 10
    ADMIN_USER_DEFAULT       = "admin"
    ADMIN_PASS_DEFAULT       = "PARAGUASMJ2026"
    SCHEDULER_HORA           = 8
    SCHEDULER_MINUTO         = 0

    @staticmethod
    def crear_carpetas():
        for c in [Config.UPLOAD_FOLDER, Config.PDF_FOLDER,
                  Config.BACKUP_FOLDER, Config.LOG_FOLDER]:
            os.makedirs(c, exist_ok=True)

Config.crear_carpetas()
