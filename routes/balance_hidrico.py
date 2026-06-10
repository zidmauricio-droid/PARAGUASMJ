"""
routes/balance_hidrico.py — Balance hídrico SIGCA
Puntos de medición: bocatoma → entrada PTAP → salida PTAP → consumo facturado
Indicadores: IANC, IPUF, POACg, IMA
Gráfico de nivel de quebrada Santibáñez (igual al diagrama compartido)
"""
from flask import Blueprint, render_template, request, jsonify, send_file
from core.database_manager import get_db
from core.seguridad import login_requerido
from utils.audit import log_action
from datetime import date
from io import BytesIO

bh_bp = Blueprint("balance_hidrico", __name__, url_prefix="/balance")

MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
         "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

PUNTOS_MEDICION = [
    ("bocatoma",     "📍 Bocatoma / Captación"),
    ("entrada_ptap", "🔵 Entrada PTAP"),
    ("salida_ptap",  "🟢 Salida PTAP / Red distribución"),
]


@bh_bp.route("/")
@login_requerido
def panel():
    anio = request.args.get("anio", date.today().year, type=int)
    return render_template("balance/panel.html",
                           anio=anio, meses=MESES, puntos=PUNTOS_MEDICION)


@bh_bp.route("/api/anio/<int:anio>")
@login_requerido
def api_datos_anio(anio):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM balance_hidrico WHERE anio=? ORDER BY mes", (anio,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@bh_bp.route("/api/guardar", methods=["POST"])
@login_requerido
def api_guardar():
    data = request.get_json() or {}
    anio = int(data.get("anio", date.today().year))
    mes  = int(data.get("mes", 1))
    conn = get_db()

    existe = conn.execute(
        "SELECT pk_balance_id FROM balance_hidrico WHERE anio=? AND mes=?",
        (anio, mes)
    ).fetchone()

    boc  = float(data.get("bocatoma_m3")      or 0)
    ent  = float(data.get("entrada_ptap_m3")  or 0)
    sal  = float(data.get("salida_ptap_m3")   or 0)
    fac  = float(data.get("consumo_facturado_m3") or 0)
    susc = int(data.get("suscriptores")        or 0)
    prod = sal if sal > 0 else (ent if ent > 0 else boc)

    ianc = round((prod - fac) / prod * 100, 2) if prod > 0 else None
    ipuf = round(fac / susc, 2) if susc > 0 else None
    long_a = float(data.get("longitud_aduccion_km")     or 0)
    long_d = float(data.get("longitud_distribucion_km") or 0)
    ima    = round((prod - fac) / (long_a + long_d), 2) if (long_a + long_d) > 0 else None

    c = {
        "bocatoma_m3":              boc or None,
        "entrada_ptap_m3":          ent or None,
        "salida_ptap_m3":           sal or None,
        "produccion_m3":            prod or None,
        "consumo_facturado_m3":     fac or None,
        "facturado_m3":             fac or None,
        "perdidas_m3":              round(prod - fac, 2) if prod > 0 else None,
        "fallas_aduccion":          data.get("fallas_aduccion"),
        "longitud_aduccion_km":     long_a or None,
        "fallas_distribucion":      data.get("fallas_distribucion"),
        "longitud_distribucion_km": long_d or None,
        "suscriptores":             susc or None,
        "empleados":                data.get("empleados"),
        "micromedidores_instalados": data.get("micromedidores_instalados"),
        "micromedidores_efectivos":  data.get("micromedidores_efectivos"),
        "ianc_pct":                  ianc,
        "ipuf_m3_susc_mes":          ipuf,
        "ima":                       ima,
        "observaciones":             data.get("observaciones",""),
    }
    c = {k: v for k, v in c.items() if v is not None and v != ""}

    if existe:
        sets = ", ".join(f"{k}=?" for k in c)
        conn.execute(
            f"UPDATE balance_hidrico SET {sets} WHERE anio=? AND mes=?",
            list(c.values()) + [anio, mes]
        )
    else:
        c["anio"] = anio; c["mes"] = mes
        conn.execute(
            f"INSERT INTO balance_hidrico ({','.join(c)}) VALUES ({','.join('?'*len(c))})",
            list(c.values())
        )
    conn.commit(); conn.close()
    log_action(accion="BALANCE_GUARDAR", modulo="balance_hidrico",
               descripcion=f"Balance {anio}-{mes:02d}")
    return jsonify({"ok": True, "ianc": ianc, "ipuf": ipuf, "ima": ima})


@bh_bp.route("/api/lecturas")
@login_requerido
def api_lecturas():
    punto     = request.args.get("punto","")
    fecha_ini = request.args.get("fecha_ini","")
    fecha_fin = request.args.get("fecha_fin","")
    conn = get_db()
    sql  = "SELECT * FROM lecturas_macromedidor WHERE 1=1"
    p    = []
    if punto:     sql += " AND punto=?";     p.append(punto)
    if fecha_ini: sql += " AND fecha>=?";    p.append(fecha_ini)
    if fecha_fin: sql += " AND fecha<=?";    p.append(fecha_fin)
    rows = conn.execute(sql + " ORDER BY fecha DESC LIMIT 500", p).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@bh_bp.route("/api/lecturas", methods=["POST"])
@login_requerido
def api_registrar_lectura():
    data = request.get_json() or {}
    conn = get_db()
    conn.execute("""
        INSERT INTO lecturas_macromedidor
        (fecha, punto, lectura_m3, caudal_lps, turbiedad_ntu, cloro_mg_l, observaciones)
        VALUES (?,?,?,?,?,?,?)
    """, (data.get("fecha", date.today().isoformat()),
          data.get("punto","bocatoma"),
          float(data.get("lectura_m3",0)),
          data.get("caudal_lps"), data.get("turbiedad_ntu"),
          data.get("cloro_mg_l"), data.get("observaciones","")))
    conn.commit(); conn.close()
    return jsonify({"ok": True}), 201


@bh_bp.route("/api/quebrada")
@login_requerido
def api_quebrada():
    """Nivel de quebrada Santibáñez con análisis de comportamiento."""
    anio = request.args.get("anio", date.today().year, type=int)
    conn = get_db()
    rows = conn.execute("""
        SELECT strftime('%m',fecha) as mes_num,
               AVG(nivel_cm) as nivel_promedio,
               MAX(nivel_cm) as nivel_max,
               MIN(nivel_cm) as nivel_min,
               COUNT(*) as n_registros,
               SUM(CASE WHEN nivel_alerta='rojo' THEN 1 ELSE 0 END) as dias_rojo,
               SUM(CASE WHEN nivel_alerta='naranja' THEN 1 ELSE 0 END) as dias_naranja
        FROM niveles_quebrada
        WHERE strftime('%Y',fecha)=?
        GROUP BY mes_num ORDER BY mes_num
    """, (str(anio),)).fetchall()
    conn.close()
    datos_mes = {int(r["mes_num"]): dict(r) for r in rows}
    # Completar los 12 meses
    serie = []
    for m in range(1, 13):
        d = datos_mes.get(m, {})
        serie.append({
            "mes":           m,
            "mes_nombre":    MESES[m-1],
            "nivel_promedio": round(d.get("nivel_promedio") or 0, 1),
            "nivel_max":      round(d.get("nivel_max") or 0, 1),
            "nivel_min":      round(d.get("nivel_min") or 0, 1),
            "dias_rojo":      d.get("dias_rojo", 0),
            "dias_naranja":   d.get("dias_naranja", 0),
        })
    return jsonify({"anio": anio, "serie": serie,
                    "umbral_critico_cm": 30, "meses": MESES})


@bh_bp.route("/api/indicadores/<int:anio>")
@login_requerido
def api_indicadores(anio):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM balance_hidrico WHERE anio=? ORDER BY mes", (anio,)
    ).fetchall()
    conn.close()
    meses = [dict(r) for r in rows]
    prod_t = sum(r.get("produccion_m3") or 0 for r in meses)
    fac_t  = sum(r.get("consumo_facturado_m3") or r.get("facturado_m3") or 0 for r in meses)
    return jsonify({
        "anio": anio, "meses": meses,
        "totales": {
            "produccion_m3":  round(prod_t, 2),
            "facturado_m3":   round(fac_t, 2),
            "perdidas_m3":    round(prod_t - fac_t, 2),
            "ianc_anual":     round((prod_t-fac_t)/prod_t*100, 2) if prod_t > 0 else None,
        }
    })


@bh_bp.route("/exportar")
@login_requerido
def exportar():
    import pandas as pd
    from openpyxl.styles import Font, PatternFill, Alignment
    anio = request.args.get("anio", date.today().year, type=int)
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM balance_hidrico WHERE anio=? ORDER BY mes", (anio,)
    ).fetchall()
    cfg  = {r["clave"]:r["valor"] for r in
            conn.execute("SELECT clave,valor FROM configuracion").fetchall()}
    conn.close()

    output = BytesIO()
    azul_f = PatternFill("solid", fgColor="1E3A8A")

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        cols = ["Mes","Bocatoma (m³)","Entrada PTAP (m³)","Salida PTAP (m³)",
                "Consumo Facturado (m³)","Pérdidas (m³)","IANC (%)","IPUF",
                "Fallas Aducción","L.Aducción (km)","Fallas Dist.","L.Dist.(km)","IMA"]
        filas = []
        for r in rows:
            d = dict(r)
            filas.append([MESES[d.get("mes",1)-1],
                d.get("bocatoma_m3",""), d.get("entrada_ptap_m3",""),
                d.get("salida_ptap_m3",""), d.get("consumo_facturado_m3",""),
                d.get("perdidas_m3",""), d.get("ianc_pct",""),
                d.get("ipuf_m3_susc_mes",""), d.get("fallas_aduccion",""),
                d.get("longitud_aduccion_km",""), d.get("fallas_distribucion",""),
                d.get("longitud_distribucion_km",""), d.get("ima","")])
        pd.DataFrame(filas, columns=cols).to_excel(
            writer, sheet_name=f"Balance {anio}", index=False)

        for ws in writer.book.worksheets:
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF", name="Calibri")
                cell.fill = azul_f
                cell.alignment = Alignment(horizontal="center")
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(
                    max(len(str(c.value or ""))+3 for c in col), 28)

    output.seek(0)
    return send_file(output, as_attachment=True,
                     download_name=f"BalanceHidrico_SIGCA_{anio}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# Compatibilidad con rutas antiguas
@bh_bp.route("/lectura/nueva")
@login_requerido
def lectura_nueva():
    return panel()
