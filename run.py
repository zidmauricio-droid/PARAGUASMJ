#!/usr/bin/env python
"""PARAGUASMJ — Lanzador principal."""
import webbrowser, threading, time, sys, os, socket, logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
logger = logging.getLogger("run")

def _base():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _base()
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

def puerto_disponible(puerto: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try: s.bind(("127.0.0.1", puerto)); return True
        except OSError: return False

def abrir_navegador(puerto: int, reintentos: int = 10, intervalo: float = 1.5):
    import urllib.request
    for i in range(reintentos):
        time.sleep(intervalo)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{puerto}/login", timeout=2)
            webbrowser.open(f"http://127.0.0.1:{puerto}/")
            logger.info("Navegador abierto correctamente.")
            return
        except Exception:
            pass
    webbrowser.open(f"http://127.0.0.1:{puerto}/")

def main():
    PORT = 5000

    if not puerto_disponible(PORT):
        logger.warning(f"Puerto {PORT} ocupado — el sistema puede ya estar corriendo.")
        webbrowser.open(f"http://127.0.0.1:{PORT}/")
        time.sleep(3)
        return

    print("=" * 56)
    print("  PARAGUASMJ")
    print("  Sistema de Gestion para Acueductos Rurales de Colombia")
    print("  Acueducto Comunitario El Puente — Villeta")
    print("=" * 56)
    print(f"  http://127.0.0.1:{PORT}")
    print("  Usuario: admin / Clave: PARAGUASMJ2026")
    print("=" * 56)

    try:
        from app import app, inicializar_app
        inicializar_app()
    except Exception as e:
        logger.error(f"Error en inicialización: {e}")
        input("Presione Enter para salir...")
        sys.exit(1)

    threading.Thread(target=abrir_navegador, args=(PORT,), daemon=True).start()

    try:
        from waitress import serve
        serve(app, host="127.0.0.1", port=PORT, threads=4,
              connection_limit=100, channel_timeout=60)
    except ImportError:
        app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)
    except Exception as e:
        logger.exception(f"Error fatal: {e}")
        input("Presione Enter para salir...")
        sys.exit(1)

if __name__ == "__main__":
    main()
