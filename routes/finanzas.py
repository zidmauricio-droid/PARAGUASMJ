"""
routes/finanzas.py
Modulo financiero: Caja menor, Bancos, Movimientos.
Fuente: PROGRAMA_1.doc seccion 'Entidades principales' (adaptado de VBA a Flask).
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from core.database_manager import get_db
from core.seguridad import login_requerido, rol_requerido
from core.auditoria import auditar
from utils.seguridad import verificar_token_csrf
from datetime import datetime, date
from functools import wraps
from io import BytesIO, StringIO
import csv

fin_bp = Blueprint("finanzas", __name__, url_prefix="/finanzas")

# Whitelist de tablas financieras — previene inyeccion via tabla
_TABLAS_FIN = frozenset({"caja_chica", "movimientos_financieros"})


import re as _re
import logging as _logging
_log_fin = _logging.getLogger("sigca.finanzas")


def _sanitizar_texto(texto: str, max_len: int = 100, allow_newlines: bool = False) -> str:
    """Limpia texto de caracteres de control y trunca.
    allow_newlines=True conserva saltos de línea (para textarea financiero).
    """
    if not texto:
        return ""
    if allow_newlines:
        texto = _re.sub(r"[\t\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", texto)
        texto = _re.sub(r"\r\n|\r", "\n", texto)
        texto = _re.sub(r"[ \t]+", " ", texto)
        texto = "\n".join(line.strip() for line in texto.split("\n"))
        texto = _re.sub(r"\n{3,}", "\n\n", texto)
    else:
        texto = _re.sub(r"[\n\r\t\x00-\x1f\x7f]", " ", texto)
        texto = _re.sub(r"\s+", " ", texto)
    return texto.strip()[:max_len]


def _validar_tabla(tabla: str) -> None:
    if tabla not in _TABLAS_FIN:
        raise ValueError(f"Tabla financiera '{tabla}' no autorizada")


def _saldo_anterior(conn, tabla: str, fecha_desde, cuenta_id=None) -> float:
    _validar_tabla(tabla)
    params = [fecha_desde]
    where = "WHERE fecha < ?"
    if cuenta_id and tabla == "movimientos_financieros":
        where += " AND fk_banco_id = ?"
        params.append(cuenta_id)

    row = conn.execute(f"""
        SELECT
            COALESCE(SUM(CASE WHEN tipo_mov='INGRESO' THEN importe ELSE 0 END),0) as ing,
            COALESCE(SUM(CASE WHEN tipo_mov='EGRESO'  THEN importe ELSE 0 END),0) as egr
        FROM {tabla} {where}
    """, params).fetchone()
    return float(row["ing"]) - float(row["egr"])


def _movimientos_con_saldo(conn, tabla: str, fecha_desde: str, fecha_hasta: str,
                            cuenta_id=None, limit: int = None, offset: int = 0) -> tuple:
    _validar_tabla(tabla)
    saldo_ant = _saldo_anterior(conn, tabla, fecha_desde, cuenta_id)

    params = [fecha_desde, fecha_hasta]
    where = "WHERE fecha >= ? AND fecha <= ?"
    if cuenta_id and tabla == "movimientos_financieros":
        where += " AND fk_banco_id = ?"
        params.append(cuenta_id)

    pk_col = "pk_mov_id" if tabla == "movimientos_financieros" else "pk_caja_id"

    total = conn.execute(
        f"SELECT COUNT(*) FROM {tabla} {where}", params
    ).fetchone()[0]

    sql = f"""
        SELECT {pk_col} as _id, fecha, concepto, importe, tipo_mov,
               COALESCE(usuario,'') as usuario
        FROM {tabla} {where} ORDER BY fecha ASC, {pk_col} ASC
    """
    pag_params = list(params)
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        pag_params += [limit, offset]

    try:
        filas = conn.execute(sql, pag_params).fetchall()
    except Exception:
        sql_fb = sql.replace(f"{pk_col} as _id", "rowid as _id").replace(
            f"ORDER BY fecha ASC, {pk_col} ASC", "ORDER BY fecha ASC, rowid ASC"
        )
        filas = conn.execute(sql_fb, pag_params).fetchall()

    saldo = saldo_ant
    resultado = []
    for row in filas:
        try:
            importe = float(row["importe"] or 0)
        except (TypeError, ValueError):
            importe = 0.0
        tipo = str(row["tipo_mov"] or "").upper()
        ing  = importe if tipo == "INGRESO" else 0.0
        egr  = importe if tipo == "EGRESO"  else 0.0
        saldo = saldo + ing - egr
        resultado.append({
            "id":       row["_id"],
            "fecha":    row["fecha"] or "",
            "concepto": row["concepto"] or "",
            "ingreso":  ing,
            "egreso":   egr,
            "saldo":    round(saldo, 2),
            "tipo_mov": tipo,
            "usuario":  row["usuario"] or ""
        })

    return resultado, saldo_ant, total


def _verificar_csrf_o_abortar():
    if not verificar_token_csrf():
        flash("Solicitud inválida. Por favor recargue la página e intente de nuevo.", "danger")
        return False
    return True


def csrf_protegido(f):
    """Decorador CSRF para endpoints POST del módulo financiero."""
    @wraps(f)
    def _wrapper(*args, **kwargs):
        if request.method == "POST" and not verificar_token_csrf():
            flash("Token de seguridad inválido. Recargue la página e intente de nuevo.", "danger")
            referrer = request.referrer or url_for("finanzas.bancos")
            return redirect(referrer)
        return f(*args, **kwargs)
    return _wrapper


# ── Caja Menor ──────────────────────────────────────────────────────
@fin_bp.route("/caja")
@login_requerido
def caja():
    hoy = date.today().isoformat()
    mes_inicio = date.today().replace(day=1).isoformat()
    return render_template("finanzas/caja.html",
                            fecha_desde=mes_inicio, fecha_hasta=hoy)


@fin_bp.route("/caja/consultar")
@login_requerido
def caja_consultar():
    fd = request.args.get("fecha_desde", date.today().replace(day=1).isoformat())
    fh = request.args.get("fecha_hasta", date.today().isoformat())
    conn = get_db()
    movs, saldo_ant, total = _movimientos_con_saldo(conn, "caja_chica", fd, fh)
    conn.close()
    return jsonify({"saldo_anterior": round(saldo_ant, 2), "movimientos": movs,
                    "fecha_desde": fd, "fecha_hasta": fh, "total": total})


@fin_bp.route("/caja/nuevo", methods=["POST"])
@login_requerido
@csrf_protegido
def caja_nuevo():
    try:
        importe = float(request.form["importe"])
        if importe <= 0:
            flash("El importe debe ser mayor a cero.", "danger")
            return redirect(url_for("finanzas.caja"))
    except (ValueError, KeyError):
        flash("Importe inválido. Ingrese un número mayor a cero.", "danger")
        return redirect(url_for("finanzas.caja"))

    concepto = _sanitizar_texto(request.form.get("concepto", ""), 500, allow_newlines=True)
    if not concepto:
        flash("El concepto es obligatorio.", "danger")
        return redirect(url_for("finanzas.caja"))

    tipo_mov = request.form.get("tipo_mov", "EGRESO")
    if tipo_mov not in ("INGRESO", "EGRESO"):
        tipo_mov = "EGRESO"
    fecha    = request.form.get("fecha", date.today().isoformat())
    usuario  = session.get("nombre_usuario", "anonimo")

    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""
            INSERT INTO caja_chica (fecha, concepto, tipo_mov, importe, usuario)
            VALUES (?, ?, ?, ?, ?)
        """, (fecha, concepto, tipo_mov, importe, usuario))
        conn.commit()
        auditar(
            "CAJA_NUEVO",
            detalle=f"{tipo_mov} | {concepto} | ${importe:,.0f} | {fecha}",
            modulo="finanzas"
        )
        flash("Movimiento registrado exitosamente.", "success")
    except Exception as e:
        conn.rollback()
        _log_fin.error("caja_nuevo: %s", e, exc_info=True)
        flash("Error al registrar el movimiento. Contacte al administrador.", "danger")
    finally:
        conn.close()
    return redirect(url_for("finanzas.caja"))


@fin_bp.route("/caja/eliminar/<int:mov_id>", methods=["POST"])
@login_requerido
@rol_requerido("admin", "tesorera")
@csrf_protegido
def caja_eliminar(mov_id):

    conn = get_db()
    try:
        reg = conn.execute(
            "SELECT fecha, concepto, tipo_mov, importe FROM caja_chica WHERE pk_caja_id=?",
            (mov_id,)
        ).fetchone()
        if not reg:
            flash("Movimiento no encontrado.", "warning")
            return redirect(url_for("finanzas.caja"))

        detalle_previo = (
            f"ELIMINADO | {reg['tipo_mov']} | {reg['concepto']} "
            f"| ${float(reg['importe']):,.0f} | {reg['fecha']}"
        )
        conn.execute("DELETE FROM caja_chica WHERE pk_caja_id=?", (mov_id,))
        conn.commit()
        auditar("CAJA_ELIMINAR", detalle=detalle_previo, modulo="finanzas")
        flash("Movimiento eliminado.", "info")
    except Exception as e:
        conn.rollback()
        _log_fin.error("caja_eliminar mov_id=%s: %s", mov_id, e, exc_info=True)
        flash("Error al eliminar el movimiento. Contacte al administrador.", "danger")
    finally:
        conn.close()
    return redirect(url_for("finanzas.caja"))


@fin_bp.route("/caja/exportar")
@login_requerido
def caja_exportar():
    fd = request.args.get("desde", date.today().replace(day=1).isoformat())
    fh = request.args.get("hasta", date.today().isoformat())
    conn = get_db()
    movs, saldo_ant, _ = _movimientos_con_saldo(conn, "caja_chica", fd, fh)
    conn.close()

    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Caja Menor"
        ws.append(["Fecha", "Concepto", "Tipo", "Ingreso", "Egreso", "Saldo", "Usuario"])
        for m in movs:
            ws.append([m["fecha"], m["concepto"], m["tipo_mov"],
                       m["ingreso"] or "", m["egreso"] or "", m["saldo"], m.get("usuario", "")])
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        return send_file(buf, as_attachment=True,
                         download_name=f"CajaMenor_SIGCA_{fd}_{fh}.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except ImportError:
        buf = StringIO()
        writer = csv.DictWriter(buf, fieldnames=["fecha", "concepto", "ingreso", "egreso", "saldo", "usuario"])
        writer.writeheader()
        writer.writerows(movs)
        buf.seek(0)
        return send_file(
            BytesIO(buf.getvalue().encode("utf-8-sig")),
            as_attachment=True,
            download_name=f"CajaMenor_SIGCA_{fd}_{fh}.csv",
            mimetype="text/csv"
        )


# ── Bancos ───────────────────────────────────────────────────────────
@fin_bp.route("/bancos")
@login_requerido
def bancos():
    conn = get_db()
    cuentas = conn.execute("SELECT * FROM bancos ORDER BY banco_nombre").fetchall()
    conn.close()
    return render_template("finanzas/bancos.html", cuentas=cuentas)


@fin_bp.route("/bancos/crear", methods=["POST"])
@login_requerido
@rol_requerido("admin", "tesorera")
@csrf_protegido
def banco_crear():
    # Sanitización profunda de entradas
    codigo    = _sanitizar_texto(request.form.get("codigo_cuenta", ""), 20).upper()
    nombre    = _sanitizar_texto(request.form.get("banco_nombre", ""), 100)
    ejecutivo = _sanitizar_texto(request.form.get("ejecutivo", ""), 80)
    telefono  = _sanitizar_texto(request.form.get("telefono", ""), 20)
    moneda    = request.form.get("moneda", "COP")
    if moneda not in ("COP", "USD", "EUR"):
        moneda = "COP"

    if not codigo or not nombre:
        flash("Código y nombre del banco son obligatorios.", "danger")
        return redirect(url_for("finanzas.bancos"))

    # Formato código: solo mayúsculas, números, guiones y guión bajo
    if not _re.match(r'^[A-Z0-9\-_]+$', codigo):
        flash("El código solo puede contener letras mayúsculas, números, guiones y guión bajo.", "danger")
        return redirect(url_for("finanzas.bancos"))

    tipo_cuenta = request.form.get("tipo_cuenta", "AHORRO")
    if tipo_cuenta not in ("AHORRO", "CORRIENTE", "EFECTIVO"):
        tipo_cuenta = "AHORRO"

    try:
        saldo_ini = float(request.form.get("saldo_inicial", 0) or 0)
        if saldo_ini < 0:
            flash("El saldo inicial no puede ser negativo.", "danger")
            return redirect(url_for("finanzas.bancos"))
    except ValueError:
        flash("Saldo inicial inválido.", "danger")
        return redirect(url_for("finanzas.bancos"))

    conn = get_db()
    try:
        # Verificar código duplicado (activa o inactiva — no reutilizar códigos)
        if conn.execute(
            "SELECT 1 FROM bancos WHERE codigo_cuenta=? AND status!='ELIMINADA'", (codigo,)
        ).fetchone():
            flash(f"Ya existe una cuenta con el código '{codigo}'.", "danger")
            return redirect(url_for("finanzas.bancos"))

        # Advertir si nombre duplicado (no bloquea)
        if conn.execute(
            "SELECT 1 FROM bancos WHERE banco_nombre=? AND status='ACTIVA'", (nombre,)
        ).fetchone():
            flash(f"Ya existe una cuenta activa con el nombre '{nombre}'. Verifique si es duplicado.", "warning")

        # Advertir saldo 0 en cuenta bancaria real
        if tipo_cuenta != "EFECTIVO" and saldo_ini == 0:
            flash("Para cuentas bancarias reales se recomienda ingresar el saldo inicial.", "warning")

        conn.execute("""
            INSERT INTO bancos (codigo_cuenta, banco_nombre, tipo_cuenta, moneda,
                               saldo_actual, ejecutivo, telefono, status)
            VALUES (?,?,?,?,?,?,?,?)
        """, (codigo, nombre, tipo_cuenta, moneda, saldo_ini, ejecutivo, telefono, "ACTIVA"))
        conn.commit()
        auditar(
            "BANCO_CREAR",
            detalle=f"Nueva cuenta: {codigo} | {nombre} | Saldo inicial: ${saldo_ini:,.0f}",
            modulo="finanzas"
        )
        flash("Cuenta bancaria creada correctamente.", "success")
    except Exception as e:
        conn.rollback()
        # Log completo interno; mensaje genérico al usuario (#3 — no exponer BD)
        _log_fin.error("banco_crear: %s", e, exc_info=True)
        flash("Error al crear la cuenta. Contacte al administrador si el problema persiste.", "danger")
    finally:
        conn.close()
    return redirect(url_for("finanzas.bancos"))


@fin_bp.route("/bancos/eliminar/<int:bid>", methods=["POST"])
@login_requerido
@rol_requerido("admin", "tesorera")
@csrf_protegido
def banco_eliminar(bid):

    conn = get_db()
    try:
        banco = conn.execute(
            "SELECT banco_nombre, codigo_cuenta, saldo_actual FROM bancos WHERE pk_banco_id=?",
            (bid,)
        ).fetchone()
        if not banco:
            flash("Cuenta no encontrada.", "warning")
            return redirect(url_for("finanzas.bancos"))

        n_movs = conn.execute(
            "SELECT COUNT(*) FROM movimientos_financieros WHERE fk_banco_id=?", (bid,)
        ).fetchone()[0]

        conn.execute("UPDATE bancos SET status='INACTIVA' WHERE pk_banco_id=?", (bid,))
        conn.commit()
        auditar(
            "BANCO_INACTIVAR",
            detalle=(
                f"{banco['banco_nombre']} ({banco['codigo_cuenta']}) "
                f"| Saldo: ${float(banco['saldo_actual']):,.0f} "
                f"| Movimientos registrados: {n_movs}"
            ),
            modulo="finanzas"
        )
        msg = "Cuenta inactivada."
        if n_movs > 0:
            msg += f" Esta cuenta tenía {n_movs} movimiento(s) registrado(s). Los registros históricos se conservan."
        flash(msg, "info")
    except Exception as e:
        conn.rollback()
        _log_fin.error("banco_eliminar bid=%s: %s", bid, e, exc_info=True)
        flash("Error al inactivar la cuenta. Contacte al administrador.", "danger")
    finally:
        conn.close()
    return redirect(url_for("finanzas.bancos"))


# ── Movimientos Bancarios ──────────────────────────────────────────
@fin_bp.route("/movimientos")
@login_requerido
def movimientos():
    cuenta_id = request.args.get("cuenta_id", type=int)
    fd = request.args.get("fecha_desde", date.today().replace(day=1).isoformat())
    fh = request.args.get("fecha_hasta", date.today().isoformat())
    pagina = request.args.get("pagina", 1, type=int)
    por_pagina = 100

    conn = get_db()
    cuentas = conn.execute("SELECT * FROM bancos WHERE status='ACTIVA'").fetchall()
    movs, saldo_ant, total = _movimientos_con_saldo(
        conn, "movimientos_financieros", fd, fh, cuenta_id,
        limit=por_pagina, offset=(pagina - 1) * por_pagina
    )
    conn.close()

    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)
    return render_template("finanzas/movimientos.html",
                            cuentas=cuentas, cuenta_id=cuenta_id,
                            movimientos=movs, saldo_anterior=saldo_ant,
                            fecha_desde=fd, fecha_hasta=fh,
                            pagina=pagina, total_paginas=total_paginas, total=total)


@fin_bp.route("/movimientos/nuevo", methods=["POST"])
@login_requerido
@csrf_protegido
def movimiento_nuevo():
    try:
        importe = float(request.form["importe"])
        if importe <= 0:
            flash("El importe debe ser mayor a cero.", "danger")
            return redirect(url_for("finanzas.movimientos"))
    except (ValueError, KeyError):
        flash("Importe inválido. Ingrese un número mayor a cero.", "danger")
        return redirect(url_for("finanzas.movimientos"))

    concepto = _sanitizar_texto(request.form.get("concepto", ""), 500, allow_newlines=True)
    if not concepto:
        flash("El concepto es obligatorio.", "danger")
        return redirect(url_for("finanzas.movimientos"))

    tipo_mov = request.form.get("tipo_mov", "EGRESO")
    if tipo_mov not in ("INGRESO", "EGRESO"):
        tipo_mov = "EGRESO"
    fecha    = request.form.get("fecha", date.today().isoformat())
    banco_id = request.form.get("fk_banco_id") or None
    if banco_id:
        try:
            banco_id = int(banco_id)
        except ValueError:
            banco_id = None
    usuario  = session.get("nombre_usuario", "anonimo")

    conn = get_db()
    try:
        saldo_banco_anterior = None

        if banco_id:
            banco = conn.execute(
                "SELECT banco_nombre, saldo_actual FROM bancos WHERE pk_banco_id=? AND status='ACTIVA'",
                (banco_id,)
            ).fetchone()
            if not banco:
                flash("La cuenta bancaria seleccionada no está activa.", "danger")
                return redirect(url_for("finanzas.movimientos"))

            saldo_banco_anterior = float(banco["saldo_actual"])

            if tipo_mov == "EGRESO" and importe > saldo_banco_anterior:
                flash(
                    f"Fondos insuficientes. El egreso (${importe:,.0f}) supera el saldo "
                    f"disponible (${saldo_banco_anterior:,.0f}). Revise el monto o la cuenta seleccionada.",
                    "danger"
                )
                return redirect(url_for("finanzas.movimientos"))

        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""
            INSERT INTO movimientos_financieros
                (fecha, fk_banco_id, tipo_mov, concepto, importe, referencia, usuario)
            VALUES (?,?,?,?,?,?,?)
        """, (fecha, banco_id, tipo_mov, concepto, importe,
              request.form.get("referencia", ""), usuario))

        if banco_id:
            if tipo_mov == "INGRESO":
                conn.execute(
                    "UPDATE bancos SET saldo_actual=saldo_actual+? WHERE pk_banco_id=?",
                    (importe, banco_id)
                )
            else:
                conn.execute(
                    "UPDATE bancos SET saldo_actual=saldo_actual-? WHERE pk_banco_id=?",
                    (importe, banco_id)
                )
        conn.commit()

        nombre_banco = banco["banco_nombre"] if banco_id and saldo_banco_anterior is not None else "Caja"
        auditar(
            "MOV_NUEVO",
            detalle=(
                f"{tipo_mov} | {concepto} | ${importe:,.0f} | {fecha} "
                f"| Cuenta: {nombre_banco}"
                + (f" | Saldo anterior: ${saldo_banco_anterior:,.0f}" if saldo_banco_anterior is not None else "")
            ),
            modulo="finanzas"
        )
        flash("Movimiento bancario registrado.", "success")
    except Exception as e:
        conn.rollback()
        _log_fin.error("movimiento_nuevo: %s", e, exc_info=True)
        flash("Error al registrar el movimiento. Contacte al administrador.", "danger")
    finally:
        conn.close()
    return redirect(url_for("finanzas.movimientos"))


# ── Ruta legada banco_nuevo (compatibilidad) ─────────────────────────────
@fin_bp.route("/bancos/nuevo", methods=["POST"])
@login_requerido
@rol_requerido("admin", "tesorera")
def banco_nuevo():
    """Alias de banco_crear — mantiene compatibilidad con formularios anteriores."""
    return banco_crear()


# ── Plan de Cuentas ───────────────────────────────────────────────────
@fin_bp.route("/plan-cuentas")
@login_requerido
def plan_cuentas():
    return render_template("finanzas/plan_cuentas.html")


@fin_bp.route("/api/plan-cuentas")
@login_requerido
def api_plan_cuentas():
    tipo = request.args.get("tipo", "").upper()
    conn = get_db()
    try:
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "fin_plan_cuentas" not in tablas:
            return jsonify({"ok": False, "error": "Tabla no disponible"})
        q = "SELECT * FROM fin_plan_cuentas WHERE activo=1"
        params = []
        if tipo in ("INGRESO", "GASTO"):
            q += " AND tipo=?"
            params.append(tipo)
        q += " ORDER BY orden, codigo"
        rows = conn.execute(q, params).fetchall()
        return jsonify({"ok": True, "cuentas": [dict(r) for r in rows]})
    finally:
        conn.close()


# ── Transacciones mensuales ───────────────────────────────────────────
@fin_bp.route("/transacciones")
@login_requerido
def transacciones():
    return render_template("finanzas/transacciones.html")


@fin_bp.route("/api/transacciones")
@login_requerido
def api_transacciones_get():
    anio = int(request.args.get("anio", date.today().year))
    mes  = request.args.get("mes", "")
    solo_pendientes = request.args.get("pendientes", "0") == "1"
    conn = get_db()
    try:
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "fin_transacciones" not in tablas:
            return jsonify({"ok": False, "error": "Módulo no inicializado"})
        q = """
            SELECT t.*, c.nombre as nombre_cuenta
            FROM fin_transacciones t
            LEFT JOIN fin_plan_cuentas c ON c.codigo = t.cod_cuenta
            WHERE t.anio=?
        """
        params = [anio]
        if mes:
            q += " AND t.mes=?"
            params.append(int(mes))
        if solo_pendientes:
            q += " AND t.estado_pago='PENDIENTE'"
        q += " ORDER BY t.fecha_registro, t.pk_trans_id"
        rows = conn.execute(q, params).fetchall()
        data = [dict(r) for r in rows]

        # KPIs del período
        ingresos = sum(r["valor"] for r in data if r["tipo"] == "INGRESO")
        gastos   = sum(r["valor"] for r in data if r["tipo"] == "GASTO")
        pendientes = sum(r["valor"] for r in data if r["estado_pago"] == "PENDIENTE")
        return jsonify({
            "ok": True,
            "transacciones": data,
            "kpis": {
                "total_ingresos": round(ingresos, 2),
                "total_gastos": round(gastos, 2),
                "saldo_neto": round(ingresos - gastos, 2),
                "pendientes": round(pendientes, 2),
                "count": len(data),
            }
        })
    finally:
        conn.close()


@fin_bp.route("/api/transacciones", methods=["POST"])
@login_requerido
def api_transacciones_post():
    d = request.get_json(silent=True) or {}
    required = ("fecha_registro", "cod_cuenta", "descripcion", "valor", "tipo")
    for f in required:
        if not d.get(f):
            return jsonify({"ok": False, "error": f"Campo requerido: {f}"})

    tipo = str(d["tipo"]).upper()
    if tipo not in ("INGRESO", "GASTO"):
        return jsonify({"ok": False, "error": "tipo debe ser INGRESO o GASTO"})

    try:
        valor = abs(float(d["valor"]))
        if valor <= 0:
            return jsonify({"ok": False, "error": "valor debe ser mayor a 0"})
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "valor inválido"})

    fecha = str(d["fecha_registro"])[:10]
    try:
        from datetime import datetime as _dt
        dt = _dt.strptime(fecha, "%Y-%m-%d")
        anio, mes = dt.year, dt.month
    except ValueError:
        return jsonify({"ok": False, "error": "fecha_registro inválida (use YYYY-MM-DD)"})

    estado_pago = str(d.get("estado_pago", "PENDIENTE")).upper()
    if estado_pago not in ("PAGADO", "PENDIENTE", "NO_APLICA"):
        estado_pago = "PENDIENTE"

    conn = get_db()
    try:
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "fin_transacciones" not in tablas:
            return jsonify({"ok": False, "error": "Módulo no inicializado"})
        cur = conn.execute("""
            INSERT INTO fin_transacciones
            (anio, mes, fecha_registro, cod_cuenta, descripcion, valor, tipo,
             fecha_pago, estado_pago, es_recurrente, observacion, usuario)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            anio, mes, fecha,
            str(d["cod_cuenta"]),
            _sanitizar_texto(str(d["descripcion"]), 300, allow_newlines=False),
            valor, tipo,
            str(d.get("fecha_pago", "") or "")[:10] or None,
            estado_pago,
            1 if d.get("es_recurrente") else 0,
            _sanitizar_texto(str(d.get("observacion", "") or ""), 500, allow_newlines=True),
            session.get("nombre_usuario", "anonimo"),
        ))
        conn.commit()
        auditar("FIN_TRANS_NUEVA",
                detalle=f"{tipo}|{d['cod_cuenta']}|{d['descripcion']}|${valor:,.0f}|{fecha}",
                modulo="finanzas")
        return jsonify({"ok": True, "pk_trans_id": cur.lastrowid})
    except Exception as e:
        conn.rollback()
        _log_fin.error("api_transacciones_post: %s", e, exc_info=True)
        return jsonify({"ok": False, "error": "Error interno al guardar"})
    finally:
        conn.close()


@fin_bp.route("/api/transacciones/<int:trans_id>/pagar", methods=["POST"])
@login_requerido
def api_marcar_pagado(trans_id):
    fecha_pago = (request.get_json(silent=True) or {}).get(
        "fecha_pago", date.today().isoformat()
    )
    conn = get_db()
    try:
        conn.execute("""
            UPDATE fin_transacciones
            SET estado_pago='PAGADO', fecha_pago=?
            WHERE pk_trans_id=?
        """, (str(fecha_pago)[:10], trans_id))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@fin_bp.route("/api/transacciones/<int:trans_id>", methods=["DELETE"])
@login_requerido
@rol_requerido("admin", "tesorera")
def api_trans_eliminar(trans_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM fin_transacciones WHERE pk_trans_id=?", (trans_id,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@fin_bp.route("/api/resumen-mensual")
@login_requerido
def api_resumen_mensual():
    """KPIs agrupados por mes para el año dado."""
    anio = int(request.args.get("anio", date.today().year))
    conn = get_db()
    try:
        tablas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "fin_transacciones" not in tablas:
            return jsonify({"ok": False, "error": "Módulo no inicializado"})
        rows = conn.execute("""
            SELECT mes,
                   SUM(CASE WHEN tipo='INGRESO' THEN valor ELSE 0 END) as ingresos,
                   SUM(CASE WHEN tipo='GASTO'   THEN valor ELSE 0 END) as gastos,
                   COUNT(*) as transacciones
            FROM fin_transacciones
            WHERE anio=?
            GROUP BY mes ORDER BY mes
        """, (anio,)).fetchall()
        meses_nombres = ["","Ene","Feb","Mar","Abr","May","Jun",
                         "Jul","Ago","Sep","Oct","Nov","Dic"]
        data = []
        for r in rows:
            data.append({
                "mes": r["mes"],
                "nombre": meses_nombres[r["mes"]],
                "ingresos": round(float(r["ingresos"] or 0), 2),
                "gastos":   round(float(r["gastos"]   or 0), 2),
                "neto":     round(float(r["ingresos"] or 0) - float(r["gastos"] or 0), 2),
                "transacciones": r["transacciones"],
            })
        return jsonify({"ok": True, "anio": anio, "meses": data})
    finally:
        conn.close()
