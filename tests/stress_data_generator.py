"""
tests/stress_data_generator.py — Generador de datos de estrés RC5.5.2
Genera volumen alto para pruebas de rendimiento:
  - 100 000 registros en registro_central
  - 50 000 movimientos financieros
  - 20 000 PQRS

Uso:
    python tests/stress_data_generator.py --help
    python tests/stress_data_generator.py --target /ruta/paraguay.db
    python tests/stress_data_generator.py --target /ruta/paraguay.db --docs 1000 --fin 500 --pqrs 200

ADVERTENCIA: Solo usar en BD de prueba. Nunca en producción.
"""
import argparse
import random
import sqlite3
import sys
import os
import time
from datetime import date, timedelta

# Agrega el directorio raíz al path para importar config si está disponible
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ESTADOS_DOC   = ["Borrador", "En_revision", "En_autorizacion", "Aprobado", "Archivado"]
TIPOS_DOC     = ["Resolución", "Acta", "Oficio", "Circular", "Informe", "Contrato", "Memo"]
ESTADOS_PQRS  = ["Recibida", "En_tramite", "Respondida", "Cerrada"]
TIPOS_PQRS    = ["Peticion", "Queja", "Reclamo", "Sugerencia", "Denuncia"]
TIPOS_MOV     = ["Ingreso", "Egreso", "Transferencia"]
RAZONES       = ["ASUACAP", "Alcaldía Villeta", "CAR", "Usuario {n}", "Proveedor {n}", "SSPD"]


def _fecha_aleatoria(inicio: date, fin: date) -> str:
    delta = (fin - inicio).days
    return (inicio + timedelta(days=random.randint(0, delta))).isoformat()


def generar_registro_central(conn: sqlite3.Connection, n: int, batch: int = 500) -> None:
    print(f"  Generando {n:,} documentos en registro_central...", end=" ", flush=True)
    t0 = time.time()
    hoy = date.today()
    inicio = date(2020, 1, 1)
    datos = []
    for i in range(1, n + 1):
        fecha = _fecha_aleatoria(inicio, hoy)
        anio = fecha[:4]
        codigo = f"STRESS-{anio}-{i:06d}"
        estado = random.choice(ESTADOS_DOC)
        tipo = random.choice(TIPOS_DOC)
        asunto = f"Documento de prueba #{i} - {tipo} generado para stress test RC5.5.2"
        datos.append((codigo, asunto, estado, tipo, fecha))
        if len(datos) >= batch:
            conn.executemany(
                "INSERT OR IGNORE INTO registro_central (codigo_completo, asunto_resumen, estado, tipo_documental, fecha_radicacion) VALUES (?,?,?,?,?)",
                datos
            )
            conn.commit()
            datos = []
    if datos:
        conn.executemany(
            "INSERT OR IGNORE INTO registro_central (codigo_completo, asunto_resumen, estado, tipo_documental, fecha_radicacion) VALUES (?,?,?,?,?)",
            datos
        )
        conn.commit()
    print(f"OK ({time.time()-t0:.1f}s)")


def generar_movimientos_financieros(conn: sqlite3.Connection, n: int, batch: int = 500) -> None:
    print(f"  Generando {n:,} movimientos financieros...", end=" ", flush=True)
    t0 = time.time()
    hoy = date.today()
    inicio = date(2020, 1, 1)
    # Obtener bancos disponibles
    bancos = [r[0] for r in conn.execute("SELECT pk_banco_id FROM bancos LIMIT 5").fetchall()]
    if not bancos:
        bancos = [None]
    datos = []
    for i in range(1, n + 1):
        fecha = _fecha_aleatoria(inicio, hoy)
        tipo = random.choice(TIPOS_MOV)
        valor = round(random.uniform(10_000, 5_000_000), 2)
        banco_id = random.choice(bancos)
        concepto = f"Movimiento stress #{i} - {tipo}"
        datos.append((fecha, tipo, valor, banco_id, concepto))
        if len(datos) >= batch:
            conn.executemany(
                "INSERT INTO movimientos_financieros (fecha, tipo_mov, valor, fk_banco_id, concepto) VALUES (?,?,?,?,?)",
                datos
            )
            conn.commit()
            datos = []
    if datos:
        conn.executemany(
            "INSERT INTO movimientos_financieros (fecha, tipo_mov, valor, fk_banco_id, concepto) VALUES (?,?,?,?,?)",
            datos
        )
        conn.commit()
    print(f"OK ({time.time()-t0:.1f}s)")


def generar_pqrs(conn: sqlite3.Connection, n: int, batch: int = 500) -> None:
    print(f"  Generando {n:,} PQRS...", end=" ", flush=True)
    t0 = time.time()
    hoy = date.today()
    inicio = date(2020, 1, 1)
    # Obtener suscriptores y registros disponibles
    suscriptores = [r[0] for r in conn.execute(
        "SELECT pk_contacto_id FROM contactos WHERE tipo_contacto='Suscriptor' LIMIT 100"
    ).fetchall()]
    registros = [r[0] for r in conn.execute(
        "SELECT pk_registro_id FROM registro_central ORDER BY pk_registro_id DESC LIMIT 1000"
    ).fetchall()]
    if not suscriptores:
        print("OMITIDO (sin suscriptores en BD)")
        return
    if not registros:
        print("OMITIDO (sin registros en BD)")
        return
    datos = []
    for i in range(1, n + 1):
        fecha_rad = _fecha_aleatoria(inicio, hoy)
        fecha_lim = (date.fromisoformat(fecha_rad) + timedelta(days=15)).isoformat()
        tipo = random.choice(TIPOS_PQRS)
        estado = random.choice(ESTADOS_PQRS)
        suscriptor_id = random.choice(suscriptores)
        registro_id = random.choice(registros)
        datos.append((tipo, estado, fecha_rad, fecha_lim, suscriptor_id, registro_id))
        if len(datos) >= batch:
            conn.executemany(
                "INSERT INTO pqrs (tipo_pqr, estado_pqr, fecha_radicacion, fecha_limite, fk_suscriptor_id, fk_registro_id) VALUES (?,?,?,?,?,?)",
                datos
            )
            conn.commit()
            datos = []
    if datos:
        conn.executemany(
            "INSERT INTO pqrs (tipo_pqr, estado_pqr, fecha_radicacion, fecha_limite, fk_suscriptor_id, fk_registro_id) VALUES (?,?,?,?,?,?)",
            datos
        )
        conn.commit()
    print(f"OK ({time.time()-t0:.1f}s)")


def verificar_indices(conn: sqlite3.Connection) -> None:
    print("  Verificando índices financieros...")
    indices = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()]
    esperados = ["idx_mov_fecha", "idx_mov_banco", "idx_mov_tipo", "idx_caja_fecha", "idx_caja_tipo"]
    for idx in esperados:
        estado = "OK" if idx in indices else "FALTA"
        print(f"    [{estado}] {idx}")


def medir_consultas(conn: sqlite3.Connection) -> None:
    print("  Midiendo rendimiento de consultas críticas...")
    consultas = [
        ("COUNT registro_central",
         "SELECT COUNT(*) FROM registro_central"),
        ("COUNT pqrs vencidas",
         f"SELECT COUNT(*) FROM pqrs WHERE fecha_limite<'{date.today().isoformat()}' AND estado_pqr NOT IN('Respondida','Cerrada')"),
        ("SUM movimientos financieros",
         "SELECT SUM(valor) FROM movimientos_financieros WHERE tipo_mov='Ingreso'"),
        ("TOP 5 documentos recientes",
         "SELECT pk_registro_id, codigo_completo FROM registro_central ORDER BY pk_registro_id DESC LIMIT 5"),
    ]
    for nombre, sql in consultas:
        t0 = time.time()
        conn.execute(sql).fetchall()
        ms = (time.time() - t0) * 1000
        estado = "OK" if ms < 500 else "LENTO"
        print(f"    [{estado}] {nombre}: {ms:.1f}ms")


def main():
    parser = argparse.ArgumentParser(
        description="Generador de datos de estrés PARAGUASMJ RC5.5.2"
    )
    parser.add_argument("--target", required=True,
                        help="Ruta a la BD SQLite de prueba (NUNCA usar en producción)")
    parser.add_argument("--docs",   type=int, default=100_000,
                        help="Registros en registro_central (default: 100000)")
    parser.add_argument("--fin",    type=int, default=50_000,
                        help="Movimientos financieros (default: 50000)")
    parser.add_argument("--pqrs",   type=int, default=20_000,
                        help="PQRS a generar (default: 20000)")
    parser.add_argument("--skip-docs",  action="store_true")
    parser.add_argument("--skip-fin",   action="store_true")
    parser.add_argument("--skip-pqrs",  action="store_true")
    parser.add_argument("--only-bench", action="store_true",
                        help="Solo ejecutar benchmark sin insertar datos")
    args = parser.parse_args()

    if not os.path.isfile(args.target):
        print(f"ERROR: BD no encontrada: {args.target}")
        print("Asegúrese de que la BD de prueba exista antes de generar datos de estrés.")
        sys.exit(1)

    print("=" * 60)
    print("PARAGUASMJ RC5.5.2 — Generador de datos de estrés")
    print(f"BD objetivo: {args.target}")
    print("ADVERTENCIA: Solo usar en BD de PRUEBA, nunca en producción")
    print("=" * 60)

    conn = sqlite3.connect(args.target, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    if not args.only_bench:
        t_total = time.time()
        if not args.skip_docs:
            generar_registro_central(conn, args.docs)
        if not args.skip_fin:
            generar_movimientos_financieros(conn, args.fin)
        if not args.skip_pqrs:
            generar_pqrs(conn, args.pqrs)
        print(f"\nInserción completada en {time.time()-t_total:.1f}s")

    print("\nVerificación post-carga:")
    verificar_indices(conn)
    medir_consultas(conn)

    conn.close()
    print("\nStress test completado.")


if __name__ == "__main__":
    main()
