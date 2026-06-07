"""
PARAGUASMJ — Limpiador de datos de instalaciones anteriores
Elimina registros de prueba, preserva configuracion y usuarios.
"""
import os, sys, shutil, sqlite3

BASE  = os.path.dirname(os.path.abspath(__file__))
DBNEW = os.path.join(BASE, "database", "paraguasmj.db")
DBOLD = os.path.join(BASE, "database", "asuacap_sigd.db")
DB    = DBNEW if os.path.exists(DBNEW) else (DBOLD if os.path.exists(DBOLD) else None)

print("=" * 58)
print("  PARAGUASMJ — Limpiando registros de instalacion previa")
print("=" * 58)

if not DB:
    print("  No se encontro base de datos. Nada que limpiar.")
    input("\n  Presione Enter..."); sys.exit(0)

print(f"  BD: {os.path.basename(DB)}")
print()

conn = sqlite3.connect(DB)
total = 0

TABLAS = [
    # Documentos
    ("contenido_documento",      "Contenido de documentos"),
    ("documentos_adjuntos",      "Adjuntos"),
    ("seguimiento_documento",    "Seguimiento"),
    ("plazos_documento",         "Plazos"),
    ("acciones_pendientes",      "Acciones pendientes"),
    ("documento_firmantes",      "Firmantes de documentos"),
    ("autorizaciones_otp",       "Autorizaciones OTP"),
    ("registro_central",         "Registro central"),
    # PQRS
    ("ordenes_trabajo",          "Ordenes de trabajo"),
    ("actas_ejecucion",          "Actas de ejecucion"),
    ("pqrs",                     "PQRS"),
    # Proyectos
    ("tareas_proyecto",          "Tareas"),
    ("metas_proyecto",           "Metas"),
    ("riesgos_proyecto",         "Riesgos"),
    ("documentos_proyecto",      "Docs de proyectos"),
    ("costos_proyecto",          "Costos"),
    ("ingresos_proyecto",        "Ingresos"),
    ("evidencias_proyecto",      "Evidencias"),
    ("proyectos",                "Proyectos"),
    # Balance
    ("balance_hidrico",          "Balance hidrico"),
    ("lecturas_macromedidor",    "Lecturas macromedidor"),
    ("niveles_quebrada",         "Niveles quebrada"),
    # Finanzas
    ("caja_movimientos",         "Caja"),
    ("banco_movimientos",        "Banco"),
    # GIS
    ("gis_reportes_fallas",      "Fallas GIS"),
    # Sistema
    ("audit_log",                "Auditoria"),
    ("logs_sistema",             "Logs"),
    ("notificaciones_historial", "Historial notif."),
    ("control_consecutivos",     "Consecutivos (reset)"),
]

for tabla, desc in TABLAS:
    try:
        n = conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        if n > 0:
            conn.execute(f"DELETE FROM {tabla}")
            try: conn.execute(f"DELETE FROM sqlite_sequence WHERE name='{tabla}'")
            except: pass
            print(f"  🗑  {desc:35s} {n:>5} registros")
            total += n
        else:
            print(f"  ✅  {desc:35s} vacía")
    except Exception as e:
        if "no such table" not in str(e):
            print(f"  ⚠   {tabla}: {e}")

conn.commit()
conn.execute("VACUUM")
conn.commit()
conn.close()

# Limpiar archivos físicos
print()
print("  Limpiando archivos físicos...")
CARPETAS = [
    os.path.join(BASE,"uploads","adjuntos"),
    os.path.join(BASE,"uploads","bitacoras"),
    os.path.join(BASE,"uploads","evidencias_proyectos"),
    os.path.join(BASE,"static","uploads","docs"),
    os.path.join(BASE,"pdfs"),
    os.path.join(BASE,"logs"),
]
for c in CARPETAS:
    if not os.path.exists(c): continue
    try:
        cnt = sum(len(f) for _,_,f in os.walk(c))
        shutil.rmtree(c)
        os.makedirs(c, exist_ok=True)
        if cnt: print(f"  🗑  {os.path.basename(c):35s} {cnt:>5} archivos")
    except Exception as e:
        print(f"  ⚠   {c}: {e}")

print()
print("  " + "=" * 54)
print(f"  ✅  Completado: {total} registros de prueba eliminados")
print(f"      Configuracion, usuarios y firmantes intactos.")
print("  " + "=" * 54)
print()
input("  Presione Enter para cerrar...")
