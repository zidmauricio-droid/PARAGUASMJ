"""
routes/finanzas.py
Modulo financiero: Caja menor, Bancos, Movimientos.
Fuente: PROGRAMA_1.doc seccion 'Entidades principales' (adaptado de VBA a Flask).
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from core.database_manager import get_db
from core.seguridad import login_requerido, rol_requerido
from core.auditoria import auditar
from datetime import datetime, date
from io import BytesIO
import pandas as pd

fin_bp = Blueprint("finanzas", __name__, url_prefix="/finanzas")


def _saldo_anterior(conn, tabla: str, fecha_desde, cuenta_id=None) -> float:
    """
    Calcula saldo anterior a fecha_desde.
    Patron de VBA: SaldoAnt + ObtenerSaldo traducido a SQLite.
    """
    where = f"WHERE fecha < '{fecha_desde}'"
    if cuenta_id and tabla == "movimientos_financieros":
        where += f" AND fk_banco_id = {cuenta_id}"
    elif tabla == "caja_chica":
        pass  # caja no filtra por cuenta

    row = conn.execute(f"""
        SELECT
            COALESCE(SUM(CASE WHEN tipo_mov='INGRESO' THEN importe ELSE 0 END),0) as ing,
            COALESCE(SUM(CASE WHEN tipo_mov='EGRESO'  THEN importe ELSE 0 END),0) as egr
        FROM {tabla} {where}
    """).fetchone()
    return float(row["ing"]) - float(row["egr"])


def _movimientos_con_saldo(conn, tabla: str, fecha_desde: str, fecha_hasta: str,
                            cuenta_id=None) -> tuple:
    """Retorna (lista_movimientos_con_saldo, saldo_anterior). Usa pk_mov_id real."""
    saldo_ant = _saldo_anterior(conn, tabla, fecha_desde, cuenta_id)

    where = f"WHERE fecha >= '{fecha_desde}' AND fecha <= '{fecha_hasta}'"
    if cuenta_id and tabla == "movimientos_financieros":
        where += f" AND fk_banco_id = {cuenta_id}"

    # Usar pk_mov_id explícito (NO rowid) para evitar errores
    pk_col = "pk_mov_id" if tabla == "movimientos_financieros" else "rowid"
    try:
        filas = conn.execute(f"""
            SELECT {pk_col} as _id, fecha, concepto, importe, tipo_mov,
                   COALESCE(usuario,'') as usuario
            FROM {tabla} {where} ORDER BY fecha ASC, {pk_col} ASC
        """).fetchall()
    except Exception:
        filas = conn.execute(f"""
            SELECT rowid as _id, fecha, concepto, importe, tipo_mov,
                   COALESCE(usuario,'') as usuario
            FROM {tabla} {where} ORDER BY fecha ASC, rowid ASC
        """).fetchall()

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

    return resultado, saldo_ant


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
    movs, saldo_ant = _movimientos_con_saldo(conn, "caja_chica", fd, fh)
    conn.close()
    return jsonify({"saldo_anterior": round(saldo_ant, 2), "movimientos": movs,
                    "fecha_desde": fd, "fecha_hasta": fh})


@fin_bp.route("/caja/nuevo", methods=["POST"])
@login_requerido
def caja_nuevo():
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO caja_chica (fecha, concepto, tipo_mov, importe, usuario)
            VALUES (?, ?, ?, ?, ?)
        """, (request.form["fecha"], request.form["concepto"].strip(),
              request.form["tipo_mov"], float(request.form["importe"]),
              session.get("nombre_usuario")))
        conn.commit()
        auditar("Movimiento caja menor registrado", modulo="finanzas")
        flash("Movimiento registrado exitosamente.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("finanzas.caja"))


@fin_bp.route("/caja/eliminar/<int:mov_id>", methods=["POST"])
@login_requerido
@rol_requerido("admin", "tesorera")
def caja_eliminar(mov_id):
    conn = get_db()
    conn.execute("DELETE FROM caja_chica WHERE pk_caja_id=?", (mov_id,))
    conn.commit(); conn.close()
    auditar(f"Movimiento caja {mov_id} eliminado", modulo="finanzas")
    flash("Movimiento eliminado.", "info")
    return redirect(url_for("finanzas.caja"))


@fin_bp.route("/caja/exportar")
@login_requerido
def caja_exportar():
    fd = request.args.get("desde", date.today().replace(day=1).isoformat())
    fh = request.args.get("hasta", date.today().isoformat())
    conn = get_db()
    movs, saldo_ant = _movimientos_con_saldo(conn, "caja_chica", fd, fh)
    conn.close()
    df = pd.DataFrame(movs)
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as wr:
        df.to_excel(wr, sheet_name="Caja Menor", index=False)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f"CajaMenor_ASUACAP_{fd}_{fh}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ── Bancos ──────────────────────────────────────────────────────────
@fin_bp.route("/bancos")
@login_requerido
def bancos():
    conn = get_db()
    cuentas = conn.execute("SELECT * FROM bancos ORDER BY banco_nombre").fetchall()
    conn.close()
    return render_template("finanzas/bancos.html", cuentas=cuentas)


@fin_bp.route("/bancos/nuevo", methods=["POST"])
@login_requerido
@rol_requerido("admin", "tesorera")
def banco_nuevo():
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO bancos (codigo_cuenta, banco_nombre, tipo_cuenta, moneda, saldo_actual, ejecutivo)
            VALUES (?,?,?,?,?,?)
        """, (request.form["codigo_cuenta"], request.form["banco_nombre"],
              request.form.get("tipo_cuenta","Ahorros"),
              request.form.get("moneda","COP"),
              float(request.form.get("saldo_actual",0)),
              request.form.get("ejecutivo","")))
        conn.commit()
        flash("Cuenta bancaria registrada.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("finanzas.bancos"))


@fin_bp.route("/movimientos")
@login_requerido
def movimientos():
    cuenta_id = request.args.get("cuenta_id", type=int)
    fd = request.args.get("fecha_desde", date.today().replace(day=1).isoformat())
    fh = request.args.get("fecha_hasta", date.today().isoformat())
    conn = get_db()
    cuentas = conn.execute("SELECT * FROM bancos WHERE status='ACTIVA'").fetchall()
    movs, saldo_ant = _movimientos_con_saldo(conn, "movimientos_financieros", fd, fh, cuenta_id)
    conn.close()
    return render_template("finanzas/movimientos.html",
                            cuentas=cuentas, cuenta_id=cuenta_id,
                            movimientos=movs, saldo_anterior=saldo_ant,
                            fecha_desde=fd, fecha_hasta=fh)


@fin_bp.route("/movimientos/nuevo", methods=["POST"])
@login_requerido
def movimiento_nuevo():
    conn = get_db()
    try:
        importe = float(request.form["importe"])
        banco_id= request.form.get("fk_banco_id") or None
        conn.execute("""
            INSERT INTO movimientos_financieros (fecha, fk_banco_id, tipo_mov, concepto, importe, referencia, usuario)
            VALUES (?,?,?,?,?,?,?)
        """, (request.form["fecha"], banco_id, request.form["tipo_mov"],
              request.form["concepto"].strip(), importe,
              request.form.get("referencia",""), session.get("nombre_usuario")))
        # Actualizar saldo del banco
        if banco_id:
            if request.form["tipo_mov"] == "INGRESO":
                conn.execute("UPDATE bancos SET saldo_actual=saldo_actual+? WHERE pk_banco_id=?", (importe, banco_id))
            else:
                conn.execute("UPDATE bancos SET saldo_actual=saldo_actual-? WHERE pk_banco_id=?", (importe, banco_id))
        conn.commit()
        flash("Movimiento bancario registrado.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("finanzas.movimientos"))


@fin_bp.route("/bancos/crear", methods=["POST"])
@login_requerido
def banco_crear():
    """Crear una nueva cuenta bancaria."""
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO bancos (codigo_cuenta, banco_nombre, tipo_cuenta, moneda,
                               saldo_actual, ejecutivo, telefono, status)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            request.form.get("codigo_cuenta","").strip().upper(),
            request.form.get("banco_nombre","").strip(),
            request.form.get("tipo_cuenta","AHORRO"),
            request.form.get("moneda","COP"),
            float(request.form.get("saldo_inicial",0) or 0),
            request.form.get("ejecutivo",""),
            request.form.get("telefono",""),
            "ACTIVA"
        ))
        conn.commit()
        flash("Cuenta bancaria creada correctamente.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error al crear cuenta: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("finanzas.bancos"))


@fin_bp.route("/bancos/eliminar/<int:bid>", methods=["POST"])
@login_requerido
def banco_eliminar(bid):
    conn = get_db()
    try:
        conn.execute("UPDATE bancos SET status='INACTIVA' WHERE pk_banco_id=?", (bid,))
        conn.commit()
        flash("Cuenta inactivada.", "info")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("finanzas.bancos"))
