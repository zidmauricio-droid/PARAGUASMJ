"""
routes/balance_hidrico.py — GA-03: Balance Hídrico y Monitoreo de Fuentes
Aplicable a cualquier prestador de servicios públicos rurales de Colombia.
- Balance mensual: macromedidor, IANC, IPUF, IMA
- Monitoreo de fuentes: generic, configurable por cliente (unidad, escala)
- Análisis automático: tendencia, estacionalidad, eventos, estadísticas
- Exportación: Excel, PDF (con openpyxl + reportlab)
"""
from flask import Blueprint, render_template, request, jsonify, send_file
from core.database_manager import get_db
from core.seguridad import login_requerido
from utils.audit import log_action
from datetime import date, datetime
from io import BytesIO
import math, statistics as _stats

bh_bp = Blueprint("balance_hidrico", __name__, url_prefix="/balance")

MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
         "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

PUNTOS_MEDICION = [
    ("bocatoma",     "Bocatoma / Captación"),
    ("entrada_ptap", "Entrada PTAP"),
    ("salida_ptap",  "Salida PTAP / Red distribución"),
]


# ══════════════════════════════════════════════════════════════════
# PANEL PRINCIPAL
# ══════════════════════════════════════════════════════════════════

@bh_bp.route("/")
@login_requerido
def panel():
    anio = request.args.get("anio", date.today().year, type=int)
    return render_template("balance/panel.html",
                           anio=anio, meses=MESES, puntos=PUNTOS_MEDICION)


# ══════════════════════════════════════════════════════════════════
# BALANCE MENSUAL (macromedidor)
# ══════════════════════════════════════════════════════════════════

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

    COLS_PERMITIDAS = frozenset({
        "bocatoma_m3","entrada_ptap_m3","salida_ptap_m3","produccion_m3",
        "consumo_facturado_m3","facturado_m3","perdidas_m3",
        "fallas_aduccion","longitud_aduccion_km",
        "fallas_distribucion","longitud_distribucion_km",
        "suscriptores","empleados","micromedidores_instalados",
        "micromedidores_efectivos","ianc_pct","ipuf_m3_susc_mes","ima","observaciones"
    })
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
    c = {k: v for k, v in c.items() if v is not None and v != "" and k in COLS_PERMITIDAS}

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


# ══════════════════════════════════════════════════════════════════
# LECTURAS MACROMEDIDOR (diarias)
# ══════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════
# FUENTES HÍDRICAS — CRUD de configuración
# ══════════════════════════════════════════════════════════════════

@bh_bp.route("/fuentes")
@login_requerido
def api_fuentes_listar():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM ga_fuentes_hidricas WHERE activo=1 ORDER BY codigo"
    ).fetchall()
    conn.close()
    return jsonify({"ok": True, "fuentes": [dict(r) for r in rows]})


@bh_bp.route("/fuentes", methods=["POST"])
@login_requerido
def api_fuentes_crear():
    data = request.get_json() or {}
    codigo      = (data.get("codigo") or "").strip().upper()
    nombre      = (data.get("nombre") or "").strip()
    tipo_fuente = (data.get("tipo_fuente") or "Quebrada").strip()
    unidad      = (data.get("unidad_medicion") or "cm").strip()
    escala_tipo = data.get("escala_tipo","libre")
    descripcion = (data.get("descripcion") or "").strip()

    if not codigo or not nombre:
        return jsonify({"ok": False, "error": "Código y nombre son obligatorios"}), 400
    if escala_tipo not in ("libre","controlada"):
        escala_tipo = "libre"

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO ga_fuentes_hidricas
            (codigo, nombre, tipo_fuente, unidad_medicion, escala_tipo, descripcion)
            VALUES (?,?,?,?,?,?)
        """, (codigo, nombre, tipo_fuente, unidad, escala_tipo, descripcion))
        fid = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
        conn.commit()
        log_action("GA03_FUENTE_CREAR", "balance_hidrico", f"{codigo} — {nombre}")
        return jsonify({"ok": True, "pk_fuente_id": fid}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        conn.close()


@bh_bp.route("/fuentes/<int:fid>", methods=["PATCH"])
@login_requerido
def api_fuentes_editar(fid):
    data = request.get_json() or {}
    campos = {}
    for f in ("nombre","tipo_fuente","unidad_medicion","escala_tipo","descripcion","activo"):
        if f in data:
            campos[f] = data[f]
    if not campos:
        return jsonify({"ok": False, "error": "Sin campos"}), 400
    conn = get_db()
    sets = ", ".join(f"{k}=?" for k in campos)
    conn.execute(f"UPDATE ga_fuentes_hidricas SET {sets} WHERE pk_fuente_id=?",
                 list(campos.values()) + [fid])
    conn.commit(); conn.close()
    return jsonify({"ok": True})


# ── Escala controlada ──────────────────────────────────────────────

@bh_bp.route("/fuentes/<int:fid>/escala")
@login_requerido
def api_escala_listar(fid):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM ga_escala_medicion WHERE fk_fuente_id=? ORDER BY orden, valor",
        (fid,)
    ).fetchall()
    conn.close()
    return jsonify({"ok": True, "escala": [dict(r) for r in rows]})


@bh_bp.route("/fuentes/<int:fid>/escala", methods=["POST"])
@login_requerido
def api_escala_guardar(fid):
    """Reemplaza toda la escala de la fuente con los valores enviados."""
    data   = request.get_json() or {}
    valores = data.get("valores", [])  # lista de floats o strings convertibles
    conn = get_db()
    try:
        conn.execute("DELETE FROM ga_escala_medicion WHERE fk_fuente_id=?", (fid,))
        for orden, v in enumerate(valores):
            try:
                val_float = float(v)
            except (ValueError, TypeError):
                continue
            conn.execute("""
                INSERT INTO ga_escala_medicion (fk_fuente_id, valor, orden)
                VALUES (?,?,?)
            """, (fid, val_float, orden))
        conn.commit()
        return jsonify({"ok": True, "n": len(valores)})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# MEDICIONES — REGISTRO Y CONSULTA
# ══════════════════════════════════════════════════════════════════

@bh_bp.route("/fuentes/<int:fid>/mediciones")
@login_requerido
def api_mediciones_listar(fid):
    fecha_ini = request.args.get("fecha_ini","")
    fecha_fin = request.args.get("fecha_fin","")
    anio      = request.args.get("anio","")
    limit     = request.args.get("limit", 500, type=int)
    conn = get_db()
    sql  = "SELECT * FROM ga_mediciones_fuente WHERE fk_fuente_id=?"
    p    = [fid]
    if fecha_ini: sql += " AND fecha>=?"; p.append(fecha_ini)
    if fecha_fin: sql += " AND fecha<=?"; p.append(fecha_fin)
    if anio:      sql += " AND strftime('%Y',fecha)=?"; p.append(str(anio))
    rows = conn.execute(sql + f" ORDER BY fecha DESC, hora DESC LIMIT {limit}", p).fetchall()
    conn.close()
    return jsonify({"ok": True, "mediciones": [dict(r) for r in rows]})


@bh_bp.route("/fuentes/<int:fid>/mediciones", methods=["POST"])
@login_requerido
def api_mediciones_registrar(fid):
    data = request.get_json() or {}
    try:
        valor = float(data.get("valor_observado", 0))
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "Valor numérico requerido"}), 400

    # Obtener unidad de la fuente
    conn = get_db()
    fuente = conn.execute(
        "SELECT unidad_medicion FROM ga_fuentes_hidricas WHERE pk_fuente_id=?", (fid,)
    ).fetchone()
    unidad = data.get("unidad") or (fuente["unidad_medicion"] if fuente else "cm")

    try:
        conn.execute("""
            INSERT INTO ga_mediciones_fuente
            (fk_fuente_id, fecha, hora, punto_medicion, valor_observado,
             unidad, nivel_alerta, responsable, observaciones)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (fid,
              data.get("fecha", date.today().isoformat()),
              data.get("hora", datetime.now().strftime("%H:%M")),
              data.get("punto_medicion","Principal"),
              valor, unidad,
              data.get("nivel_alerta","normal"),
              data.get("responsable",""),
              data.get("observaciones","")))
        conn.commit()
        log_action("GA03_MEDICION", "balance_hidrico", f"Fuente {fid}: {valor} {unidad}")
        return jsonify({"ok": True}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# ANÁLISIS AUTOMÁTICO DE FUENTE HÍDRICA
# ══════════════════════════════════════════════════════════════════

@bh_bp.route("/fuentes/<int:fid>/analisis")
@login_requerido
def api_analisis(fid):
    """
    Análisis automático: tendencia, estacionalidad, eventos, estadísticas.
    Retorna interpretación en texto para incluir en informes.
    """
    anio = request.args.get("anio", date.today().year, type=int)
    conn = get_db()

    fuente = conn.execute(
        "SELECT * FROM ga_fuentes_hidricas WHERE pk_fuente_id=?", (fid,)
    ).fetchone()
    if not fuente:
        conn.close()
        return jsonify({"ok": False, "error": "Fuente no encontrada"}), 404

    # Datos del año solicitado agrupados por mes
    rows = conn.execute("""
        SELECT strftime('%m',fecha) as mes_num,
               AVG(valor_observado)  as promedio,
               MAX(valor_observado)  as maximo,
               MIN(valor_observado)  as minimo,
               COUNT(*)              as n_registros,
               SUM(CASE WHEN nivel_alerta='rojo'    THEN 1 ELSE 0 END) as dias_rojo,
               SUM(CASE WHEN nivel_alerta='naranja' THEN 1 ELSE 0 END) as dias_naranja
        FROM ga_mediciones_fuente
        WHERE fk_fuente_id=? AND strftime('%Y',fecha)=?
        GROUP BY mes_num ORDER BY mes_num
    """, (fid, str(anio))).fetchall()

    # Datos históricos (todos los años) para tendencia multi-anual
    hist = conn.execute("""
        SELECT strftime('%Y',fecha) as anio_r,
               AVG(valor_observado) as promedio_anual
        FROM ga_mediciones_fuente
        WHERE fk_fuente_id=?
        GROUP BY anio_r ORDER BY anio_r
    """, (fid,)).fetchall()

    conn.close()

    unidad = fuente["unidad_medicion"]
    datos_mes = {int(r["mes_num"]): dict(r) for r in rows}

    # ── Serie mensual completa ──────────────────────────────────
    serie = []
    for m in range(1, 13):
        d = datos_mes.get(m, {})
        serie.append({
            "mes":         m,
            "mes_nombre":  MESES[m-1],
            "promedio":    round(d.get("promedio") or 0, 2),
            "maximo":      round(d.get("maximo")   or 0, 2),
            "minimo":      round(d.get("minimo")   or 0, 2),
            "n_registros": d.get("n_registros", 0),
            "dias_rojo":   d.get("dias_rojo",   0),
            "dias_naranja":d.get("dias_naranja", 0),
        })

    promedios = [s["promedio"] for s in serie if s["promedio"] > 0]

    # ── Estadísticas ──────────────────────────────────────────
    estadisticas = {}
    if promedios:
        estadisticas = {
            "valor_minimo":   round(min(promedios), 2),
            "valor_maximo":   round(max(promedios), 2),
            "promedio_anual": round(_stats.mean(promedios), 2),
            "n_meses_con_datos": len(promedios),
            "unidad":         unidad,
        }
        if len(promedios) >= 2:
            estadisticas["desviacion_std"] = round(_stats.stdev(promedios), 2)

    # ── Tendencia histórica ────────────────────────────────────
    tendencia = _calcular_tendencia([dict(r) for r in hist])

    # ── Periodos críticos (meses con mínimo relativo) ──────────
    criticos = []
    if promedios:
        umbral_bajo = _stats.mean(promedios) * 0.65
        for s in serie:
            if s["promedio"] > 0 and s["promedio"] < umbral_bajo:
                criticos.append(s["mes_nombre"])

    # ── Eventos atípicos ──────────────────────────────────────
    eventos = _detectar_eventos(serie)

    # ── Interpretación automática ─────────────────────────────
    interpretacion = _generar_interpretacion(
        fuente["nombre"], anio, unidad, estadisticas,
        tendencia, criticos, eventos, serie
    )

    return jsonify({
        "ok":             True,
        "fuente":         dict(fuente),
        "anio":           anio,
        "serie":          serie,
        "estadisticas":   estadisticas,
        "tendencia":      tendencia,
        "periodos_criticos": criticos,
        "eventos":        eventos,
        "interpretacion": interpretacion,
        "historico":      [dict(r) for r in hist],
    })


def _calcular_tendencia(hist: list) -> dict:
    """Regresión lineal simple sobre promedios anuales."""
    if len(hist) < 2:
        return {"tipo": "insuficiente", "descripcion": "Datos insuficientes para calcular tendencia"}
    x = list(range(len(hist)))
    y = [r.get("promedio_anual") or 0 for r in hist]
    n = len(x)
    sx, sy = sum(x), sum(y)
    sxy = sum(xi*yi for xi,yi in zip(x,y))
    sx2 = sum(xi**2 for xi in x)
    denom = n*sx2 - sx**2
    if denom == 0:
        return {"tipo": "estable", "descripcion": "Sin variación entre períodos"}
    pendiente = (n*sxy - sx*sy) / denom
    if pendiente > 0.5:
        tipo = "incremento"
        desc = f"Tendencia de INCREMENTO ({pendiente:+.2f}/año) — disponibilidad creciente."
    elif pendiente < -0.5:
        tipo = "disminucion"
        desc = f"Tendencia de DISMINUCIÓN ({pendiente:+.2f}/año) — posible reducción de caudal. Monitoreo prioritario."
    else:
        tipo = "estable"
        desc = f"Tendencia ESTABLE (variación {pendiente:+.2f}/año)."
    return {"tipo": tipo, "pendiente": round(pendiente, 3), "descripcion": desc}


def _detectar_eventos(serie: list) -> list:
    """Detecta descensos o aumentos abruptos entre meses consecutivos."""
    eventos = []
    promedios = [(s["mes_nombre"], s["promedio"]) for s in serie if s["promedio"] > 0]
    for i in range(1, len(promedios)):
        nombre, val = promedios[i]
        _, val_prev = promedios[i-1]
        if val_prev == 0:
            continue
        cambio_pct = (val - val_prev) / val_prev * 100
        if cambio_pct <= -30:
            eventos.append({
                "mes": nombre,
                "tipo": "descenso_abrupto",
                "cambio_pct": round(cambio_pct, 1),
                "descripcion": f"Descenso abrupto en {nombre}: {cambio_pct:.1f}% respecto al mes anterior."
            })
        elif cambio_pct >= 40:
            eventos.append({
                "mes": nombre,
                "tipo": "incremento_abrupto",
                "cambio_pct": round(cambio_pct, 1),
                "descripcion": f"Incremento abrupto en {nombre}: +{cambio_pct:.1f}% respecto al mes anterior."
            })
    return eventos


def _generar_interpretacion(nombre, anio, unidad, est, tendencia, criticos, eventos, serie) -> str:
    if not est:
        return f"Sin datos suficientes para {nombre} en {anio}."
    partes = [
        f"Fuente: {nombre} — Período analizado: {anio}.",
        f"Unidad de medición: {unidad}.",
        f"Se registraron datos en {est.get('n_meses_con_datos',0)} de 12 meses.",
        f"Valor mínimo observado: {est.get('valor_minimo',0)} {unidad}. "
        f"Valor máximo: {est.get('valor_maximo',0)} {unidad}. "
        f"Promedio anual: {est.get('promedio_anual',0)} {unidad}.",
    ]
    partes.append(tendencia.get("descripcion",""))
    if criticos:
        partes.append(f"Períodos de menor disponibilidad identificados: {', '.join(criticos)}. "
                      "Se recomienda medidas de ahorro y contingencia en estos meses.")
    else:
        partes.append("No se identificaron períodos críticos de baja disponibilidad en el período analizado.")
    for ev in eventos:
        partes.append(ev["descripcion"])
    return " ".join(partes)


# ══════════════════════════════════════════════════════════════════
# EXPORTACIÓN EXCEL
# ══════════════════════════════════════════════════════════════════

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


@bh_bp.route("/fuentes/<int:fid>/exportar")
@login_requerido
def exportar_fuente(fid):
    """Exporta el historial de mediciones de una fuente específica en Excel."""
    import pandas as pd
    from openpyxl.styles import Font, PatternFill, Alignment
    anio = request.args.get("anio", "", type=str)
    conn = get_db()
    fuente = conn.execute(
        "SELECT * FROM ga_fuentes_hidricas WHERE pk_fuente_id=?", (fid,)
    ).fetchone()
    if not fuente:
        conn.close()
        from flask import abort
        abort(404)

    sql = "SELECT * FROM ga_mediciones_fuente WHERE fk_fuente_id=?"
    p   = [fid]
    if anio:
        sql += " AND strftime('%Y',fecha)=?"; p.append(anio)
    rows = conn.execute(sql + " ORDER BY fecha, hora", p).fetchall()
    conn.close()

    output = BytesIO()
    azul_f = PatternFill("solid", fgColor="1E3A8A")
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        cols   = ["Fecha","Hora","Punto medición","Valor observado",
                  "Unidad","Nivel alerta","Responsable","Observaciones"]
        filas  = [[r["fecha"], r["hora"], r["punto_medicion"],
                   r["valor_observado"], r["unidad"], r["nivel_alerta"],
                   r["responsable"], r["observaciones"]] for r in rows]
        pd.DataFrame(filas, columns=cols).to_excel(
            writer, sheet_name=fuente["nombre"][:30], index=False)
        for ws in writer.book.worksheets:
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = azul_f
                cell.alignment = Alignment(horizontal="center")
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = 18

    output.seek(0)
    nombre_limpio = fuente["nombre"].replace(" ","_")[:20]
    return send_file(output, as_attachment=True,
                     download_name=f"Mediciones_{nombre_limpio}_{anio or 'completo'}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ── Ruta legacy compatibilidad ─────────────────────────────────────
@bh_bp.route("/lectura/nueva")
@login_requerido
def lectura_nueva():
    return panel()
