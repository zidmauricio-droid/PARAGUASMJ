"""
PARAGUASMJ — Descarga de TipTap para uso offline
Ejecutar con: python descargar_editor_offline.py
"""
import os, urllib.request, sys

BASE = "https://cdn.jsdelivr.net/npm/@tiptap"
DEST = os.path.join(os.path.dirname(__file__), "static", "vendor", "tiptap")
os.makedirs(DEST, exist_ok=True)

paquetes = [
    "pm", "core", "starter-kit",
    "extension-table", "extension-table-row",
    "extension-table-header", "extension-table-cell",
    "extension-image", "extension-text-align",
    "extension-link", "extension-underline",
    "extension-superscript", "extension-subscript",
    "extension-color", "extension-text-style",
    "extension-highlight", "extension-font-family",
]

print("="*55)
print("  PARAGUASMJ — Descargando editor para uso offline")
print("="*55)

ok = fail = 0
for pkg in paquetes:
    url  = f"{BASE}/{pkg}@2.4.0/dist/index.umd.js"
    dest = os.path.join(DEST, f"{pkg}.umd.js")
    try:
        print(f"  Descargando {pkg}...", end=" ", flush=True)
        urllib.request.urlretrieve(url, dest)
        size = os.path.getsize(dest)
        print(f"OK ({size//1024} KB)")
        ok += 1
    except Exception as e:
        print(f"FALLO: {e}")
        fail += 1

print(f"\n  Resultado: {ok}/{ok+fail} paquetes descargados")
if fail == 0:
    print("  ✅ Editor listo para uso offline")
else:
    print("  ⚠ Algunos fallos — intente de nuevo")
input("\nPresione Enter para salir...")
