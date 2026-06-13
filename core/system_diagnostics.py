"""
core/system_diagnostics.py — Observabilidad sistémica RC5.5.3
Mide: RAM, crecimiento de tablas, tiempos de consulta, slow-endpoints.
Sin dependencias externas (stdlib pura). Seguro para PyInstaller.
"""
import os
import sys
import time
import logging
import sqlite3
from typing import Optional

logger = logging.getLogger("sigca.diagnostics")

# ── Obtener RAM sin psutil ─────────────────────────────────────────────────────

def _ram_mb() -> float:
    """Retorna uso de RAM del proceso en MB. Funciona en Linux y Windows."""
    try:
        # Linux — /proc/self/status
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except Exception:
        pass
    try:
        # Windows — ctypes
        import ctypes
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]
        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(pmc)
        ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(pmc), pmc.cb
        )
        return pmc.WorkingSetSize / (1024 * 1024)
    except Exception:
        pass
    return -1.0


# ── Tabla de crecimiento ───────────────────────────────────────────────────────

_TABLAS_MONITOREADAS = [
    ("registro_central",    "pk_registro_id"),
    ("audit_log",           "id"),
    ("pqrs",                "pk_pqr_id"),
    ("expedientes",         "pk_expediente_id"),
    ("proyectos",           "pk_proyecto_id"),
    ("tareas_proyecto",     "id"),
    ("finanzas_caja",       "pk_mov_id"),
    ("bancos_movimientos",  "pk_mov_id"),
    ("contenido_documento", "pk_contenido_id"),
    ("contactos",           "pk_contacto_id"),
    ("usuarios",            "pk_usuario_id"),
    ("balance_hidrico",     "pk_lectura_id"),
    ("carpetas",            "pk_carpeta_id"),
]

def _contar_tabla(conn, tabla: str, pk: str) -> Optional[int]:
    try:
        row = conn.execute(f"SELECT COUNT(*) as n FROM {tabla}").fetchone()
        return row["n"] if row else 0
    except Exception:
        return None

def _tamano_db_mb(db_path: str) -> float:
    try:
        return os.path.getsize(db_path) / (1024 * 1024)
    except Exception:
        return -1.0


# ── Tiempos de consulta representativos ───────────────────────────────────────

_CONSULTAS_BENCHMARK = [
    ("documentos_listar",
     "SELECT COUNT(*) FROM registro_central WHERE estado='Borrador'"),
    ("pqrs_pendientes",
     "SELECT COUNT(*) FROM pqrs WHERE estado_pqr='Recibida'"),
    ("audit_semana",
     "SELECT COUNT(*) FROM audit_log WHERE timestamp >= date('now','-7 days')"),
    ("finanzas_mes",
     "SELECT COUNT(*) FROM finanzas_caja WHERE fecha >= date('now','start of month')"),
    ("proyectos_activos",
     "SELECT COUNT(*) FROM proyectos WHERE estado='ACTIVO'"),
    ("expedientes_abiertos",
     "SELECT COUNT(*) FROM expedientes WHERE estado='ABIERTO'"),
]

def _benchmark_consultas(conn) -> list[dict]:
    resultados = []
    for nombre, sql in _CONSULTAS_BENCHMARK:
        t0 = time.perf_counter()
        try:
            conn.execute(sql).fetchone()
            elapsed_ms = (time.perf_counter() - t0) * 1000
            resultados.append({
                "consulta": nombre,
                "ms": round(elapsed_ms, 2),
                "nivel": "OK" if elapsed_ms < 50 else ("LENTO" if elapsed_ms < 500 else "CRITICO"),
            })
        except Exception as e:
            resultados.append({
                "consulta": nombre,
                "ms": -1,
                "nivel": "ERROR",
                "error": str(e),
            })
    return resultados


# ── Índices faltantes (heurística) ────────────────────────────────────────────

def _indices_existentes(conn) -> set:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    return {r["name"] for r in rows}

def _verificar_integridad(conn) -> str:
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
        return row[0] if row else "desconocido"
    except Exception:
        return "error"

def _modo_wal(conn) -> bool:
    try:
        row = conn.execute("PRAGMA journal_mode").fetchone()
        return (row[0] or "").lower() == "wal"
    except Exception:
        return False


# ── Slow endpoints recientes ──────────────────────────────────────────────────

def _slow_endpoints_recientes(conn, limite: int = 20) -> list[dict]:
    try:
        rows = conn.execute("""
            SELECT descripcion, timestamp, nombre_usuario
            FROM audit_log
            WHERE accion='SLOW_ENDPOINT'
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limite,)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ── Función principal ─────────────────────────────────────────────────────────

def obtener_diagnostico_completo(db_path: Optional[str] = None) -> dict:
    """
    Retorna un dict con observabilidad completa del sistema.
    Seguro: captura todas las excepciones internamente.
    """
    if db_path is None:
        try:
            from config import Config
            db_path = Config.DB_PATH
        except Exception:
            db_path = "paraguasmj.db"

    resultado = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ram_mb": _ram_mb(),
        "python_version": sys.version.split()[0],
        "db_path": db_path,
        "db_existe": os.path.exists(db_path),
        "db_tamano_mb": _tamano_db_mb(db_path),
        "tablas": {},
        "benchmarks": [],
        "slow_endpoints": [],
        "integridad_db": "no_conectado",
        "modo_wal": False,
        "indices_count": 0,
        "errores": [],
    }

    if not os.path.exists(db_path):
        resultado["errores"].append(f"BD no encontrada: {db_path}")
        return resultado

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Conteo de tablas
        for tabla, pk in _TABLAS_MONITOREADAS:
            n = _contar_tabla(conn, tabla, pk)
            if n is not None:
                resultado["tablas"][tabla] = n

        # Benchmarks
        resultado["benchmarks"] = _benchmark_consultas(conn)

        # Slow endpoints recientes
        resultado["slow_endpoints"] = _slow_endpoints_recientes(conn)

        # Integridad y WAL
        resultado["integridad_db"] = _verificar_integridad(conn)
        resultado["modo_wal"] = _modo_wal(conn)
        resultado["indices_count"] = len(_indices_existentes(conn))

    except Exception as e:
        resultado["errores"].append(str(e))
        logger.error("obtener_diagnostico_completo: %s", e, exc_info=True)
    finally:
        if conn:
            conn.close()

    return resultado


def resumen_texto(diag: dict) -> str:
    """Genera resumen legible para log de arranque."""
    tablas_str = ", ".join(
        f"{k}={v}" for k, v in list(diag["tablas"].items())[:5]
    )
    return (
        f"RAM={diag['ram_mb']:.0f}MB | "
        f"BD={diag['db_tamano_mb']:.1f}MB | "
        f"WAL={'SI' if diag['modo_wal'] else 'NO'} | "
        f"indices={diag['indices_count']} | "
        f"tablas=[{tablas_str}]"
    )
