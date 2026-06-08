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
from io import BytesIO, StringIO
import csv

fin_bp = Blueprint("finanzas", __name__, url_prefix="/finanzas")

# Whitelist de tablas financieras — previene inyeccion via tabla
_TABLAS_FIN = frozenset({"caja_chica", "movimientos_financieros"})


def _validar_tabla(tabla: str) -> None:
    if tabla not in _TABLAS_FIN:
        raise ValueError(f"Tabla financiera '{tabla}' no autorizada")


def _saldo_anterior(conn, tabla: str, fecha_desde, cuenta_id=None) -> float:
    """
    Calcula saldo anterior a fecha_desde usando queries parametrizadas.
    Patron de VBA: SaldoAnt + ObtenerSaldo traducido a SQLite.
    """
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
    """
    Retorna (lista_movimientos_con_saldo, saldo_anterior, total_sin_paginar).
    limit=None retorna todos los registros (para exportacion).
    """
    _validar_tabla(tabla)
    saldo_ant = _saldo_anterior(conn, tabla, fecha_desde, cuenta_id)

    params = [fecha_desde, fecha_hasta]
    where = "WHERE fecha >= ? AND fecha <= ?"
    if cuenta_id and tabla == "movimientos_financieros":
        where += " AND fk_banco_id = ?"
        params.append(cuenta_id)

    pk_col = "pk_mov_id" if tabla == "movimientos_financieros" else "pk_caja_id"

    # Total sin paginar — para UI de paginacion
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
        # Fallback a rowid si pk_col no existe
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
    """Verifica CSRF y retorna True si OK, False si invalido (con flash)."""
    if not verificar_token_csrf():
        flash("Solicitud inválida. Por favor recargue la página e intente de nuevo.", "danger")
        return False
    return True


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
def caja_nuevo():
    if not _verificar_csrf_o_abortar():
        return redirect(url_for("finanzas.caja"))

    try:
        importe = float(request.form["importe"])
        if importe <= 0:
            flash("El importe debe ser mayor a cero.", "danger")
            return redirect(url_for("finanzas.caja"))
    except (ValueError, KeyError):
        flash("Importe inválido. Ingrese un número mayor a cero.", "danger")
        return redirect(url_for("finanzas.caja"))

    concepto = request.form.get("concepto", "").strip()
    if not concepto:
        flash("El concepto es obligatorio.", "danger")
        return redirect(url_for("finanzas.caja"))

    tipo_mov = request.form.get("tipo_mov", "EGRESO")
    fecha    = request.form.get("fecha", date.today().isoformat())
    usuario  = session.get("nombre_usuario", "anonimo")

    conn = get_db()
    try:
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
        flash(f"Error al registrar: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("finanzas.caja"))


@fin_bp.route("/caja/eliminar/<int:mov_id>", methods=["POST"])
@login_requerido
@rol_requerido("admin", "tesorera")
def caja_eliminar(mov_id):
    if not _verificar_csrf_o_abortar():
        return redirect(url_for("finanzas.caja"))

    conn = get_db()
    try:
        # Leer registro ANTES de eliminar — trazabilidad WORM
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
        flash(f"Error al eliminar: {e}", "danger")
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
        import pandas as pd
        df = pd.DataFrame(movs)
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as wr:
            df.to_excel(wr, sheet_name="Caja Menor", index=False)
        buf.seek(0)
        return send_file(buf, as_attachment=True,
                         download_name=f"CajaMenor_ASUACAP_{fd}_{fh}.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except ImportError:
        # Fallback CSV sin dependencias externas
        buf = StringIO()
        writer = csv.DictWriter(buf, fieldnames=["fecha", "concepto", "ingreso", "egreso", "saldo", "usuario"])
        writer.writeheader()
        writer.writerows(movs)
        buf.seek(0)
        return send_file(
            BytesIO(buf.getvalue().encode("utf-8-sig")),
            as_attachment=True,
            download_name=f"CajaMenor_ASUACAP_{fd}_{fh}.csv",
            mimetype="text/csv"
        )


# ── Bancos ──────────────────────────────────────────────────────────
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
def banco_crear():
    """Crear una nueva cuenta bancaria."""
    if not _verificar_csrf_o_abortar():
        return redirect(url_for("finanzas.bancos"))

    codigo  = request.form.get("codigo_cuenta", "").strip().upper()
    nombre  = request.form.get("banco_nombre", "").strip()
    if not codigo or not nombre:
        flash("Código y nombre del banco son obligatorios.", "danger")
        return redirect(url_for("finanzas.bancos"))

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
        conn.execute("""
            INSERT INTO bancos (codigo_cuenta, banco_nombre, tipo_cuenta, moneda,
                               saldo_actual, ejecutivo, telefono, status)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            codigo, nombre,
            request.form.get("tipo_cuenta", "AHORRO"),
            request.form.get("moneda", "COP"),
            saldo_ini,
            request.form.get("ejecutivo", ""),
            request.form.get("telefono", ""),
            "ACTIVA"
        ))
        conn.commit()
        auditar(
            "BANCO_CREAR",
            detalle=f"Nueva cuenta: {codigo} | {nombre} | Saldo inicial: ${saldo_ini:,.0f}",
            modulo="finanzas"
        )
        flash("Cuenta bancaria creada correctamente.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error al crear cuenta: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("finanzas.bancos"))


@fin_bp.route("/bancos/eliminar/<int:bid>", methods=["POST"])
@login_requerido
@rol_requerido("admin", "tesorera")
def banco_eliminar(bid):
    if not _verificar_csrf_o_abortar():
        return redirect(url_for("finanzas.bancos"))

    conn = get_db()
    try:
        # Leer estado previo — trazabilidad WORM
        banco = conn.execute(
            "SELECT banco_nombre, codigo_cuenta, saldo_actual FROM bancos WHERE pk_banco_id=?",
            (bid,)
        ).fetchone()
        if not banco:
            flash("Cuenta no encontrada.", "warning")
            return redirect(url_for("finanzas.bancos"))

        # Advertir si tiene movimientos activos
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
        flash(f"Error: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("finanzas.bancos"))


# ── Movimientos Bancarios ────────────────────────────────────────────
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
def movimiento_nuevo():
    if not _verificar_csrf_o_abortar():
        return redirect(url_for("finanzas.movimientos"))

    try:
        importe = float(request.form["importe"])
        if importe <= 0:
            flash("El importe debe ser mayor a cero.", "danger")
            return redirect(url_for("finanzas.movimientos"))
    except (ValueError, KeyError):
        flash("Importe inválido. Ingrese un número mayor a cero.", "danger")
        return redirect(url_for("finanzas.movimientos"))

    concepto = request.form.get("concepto", "").strip()
    if not concepto:
        flash("El concepto es obligatorio.", "danger")
        return redirect(url_for("finanzas.movimientos"))

    tipo_mov = request.form.get("tipo_mov", "EGRESO")
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

            # Bloquear EGRESO si supera saldo disponible
            if tipo_mov == "EGRESO" and importe > saldo_banco_anterior:
                flash(
                    f"Fondos insuficientes. El egreso (${importe:,.0f}) supera el saldo "
                    f"disponible (${saldo_banco_anterior:,.0f}). Revise el monto o la cuenta seleccionada.",
                    "danger"
                )
                return redirect(url_for("finanzas.movimientos"))

        # Escritura atómica: INSERT + UPDATE saldo en una sola transacción
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
        flash(f"Error al registrar movimiento: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("finanzas.movimientos"))


# ── Ruta legada banco_nuevo (compatibilidad) ─────────────────────────
@fin_bp.route("/bancos/nuevo", methods=["POST"])
@login_requerido
@rol_requerido("admin", "tesorera")
def banco_nuevo():
    """Alias de banco_crear — mantiene compatibilidad con formularios anteriores."""
    return banco_crear()
