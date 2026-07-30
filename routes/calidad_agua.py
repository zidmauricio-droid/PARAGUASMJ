"""
routes/calidad_agua.py — RC6 GA-02 Calidad de Agua
Módulo técnico estructurado. Parámetros configurables, muestras, resultados
ACEPTABLE/NO_ACEPTABLE con acciones correctivas. Norma: Res. 2115/2007.
"""
import logging
from datetime import date
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash

from core.database_manager import get_db
from core.seguridad import login_requerido
from utils.audit import log_action
from utils.seguridad import verificar_token_csrf

_log = logging.getLogger("sigca.calidad_agua")

cal_bp = Blueprint("calidad_agua", __name__, url_prefix="/calidad-agua")


# ── Panel principal ────────────────────────────────────────────────────────────

@cal_bp.route("/")
@login_requerido
def panel():
    return render_template("calidad_agua/panel.html")


# ── API: parámetros ────────────────────────────────────────────────────────────

@cal_bp.route("/api/parametros")
@login_requerido
def api_parametros():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM calidad_parametros WHERE activo=1 ORDER BY orden, nombre"
        ).fetchall()
        return jsonify({"ok": True, "parametros": [dict(r) for r in rows]})
    except Exception as e:
        _log.error("api_parametros: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


# ── API: puntos de muestreo ────────────────────────────────────────────────────

@cal_bp.route("/api/puntos")
@login_requerido
def api_puntos():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM calidad_puntos_muestreo WHERE activo=1 ORDER BY nombre"
        ).fetchall()
        return jsonify({"ok": True, "puntos": [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@cal_bp.route("/api/puntos", methods=["POST"])
@login_requerido
def api_crear_punto():
    data = request.get_json() or {}
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"ok": False, "error": "Nombre obligatorio"}), 400
    conn = get_db()
    try:
        n = conn.execute("SELECT COUNT(*) FROM calidad_puntos_muestreo").fetchone()[0]
        codigo = data.get("codigo") or f"PM-{n+1:03d}"
        conn.execute("""
            INSERT INTO calidad_puntos_muestreo (codigo, nombre, tipo, descripcion, coordenada_lat, coordenada_lon)
            VALUES (?,?,?,?,?,?)
        """, (codigo, nombre,
              data.get("tipo", "distribucion"),
              data.get("descripcion", ""),
              data.get("lat"), data.get("lon")))
        conn.commit()
        return jsonify({"ok": True, "codigo": codigo}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


# ── API: muestras ──────────────────────────────────────────────────────────────

@cal_bp.route("/api/muestras")
@login_requerido
def api_muestras():
    anio = request.args.get("anio", date.today().year, type=int)
    mes  = request.args.get("mes",  0, type=int)
    conn = get_db()
    try:
        sql = """
            SELECT m.*, p.nombre as punto_nombre
            FROM calidad_muestras m
            LEFT JOIN calidad_puntos_muestreo p ON m.fk_punto_id=p.pk_punto_id
            WHERE m.anio=?
        """
        params = [anio]
        if mes:
            sql += " AND m.mes=?"; params.append(mes)
        sql += " ORDER BY m.fecha_muestra DESC"
        rows = conn.execute(sql, params).fetchall()
        return jsonify({"ok": True, "muestras": [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@cal_bp.route("/api/muestras", methods=["POST"])
@login_requerido
def api_crear_muestra():
    data = request.get_json() or {}
    fecha = data.get("fecha_muestra") or date.today().isoformat()
    anio  = int(fecha[:4])
    mes   = int(fecha[5:7])
    conn  = get_db()
    try:
        n = conn.execute("SELECT COUNT(*) FROM calidad_muestras").fetchone()[0]
        codigo = f"CA-{anio}-{n+1:04d}"
        conn.execute("""
            INSERT INTO calidad_muestras
            (codigo_muestra, anio, mes, fecha_muestra, fk_punto_id, laboratorio, responsable, observaciones, registrado_por)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (codigo, anio, mes, fecha,
              data.get("fk_punto_id"),
              data.get("laboratorio", ""),
              data.get("responsable", ""),
              data.get("observaciones", ""),
              session.get("nombre_usuario", "")))
        muestra_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        log_action(accion="CREATE", modulo="calidad_agua",
                   descripcion=f"Muestra {codigo} registrada")
        return jsonify({"ok": True, "pk_muestra_id": muestra_id, "codigo": codigo}), 201
    except Exception as e:
        conn.rollback()
        _log.error("api_crear_muestra: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


# ── API: resultados de una muestra ─────────────────────────────────────────────

@cal_bp.route("/api/muestras/<int:mid>/resultados")
@login_requerido
def api_resultados(mid):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT r.*, p.codigo as param_codigo, p.nombre as param_nombre,
                   p.unidad, p.valor_min, p.valor_max, p.norma
            FROM calidad_resultados r
            JOIN calidad_parametros p ON r.fk_param_id=p.pk_param_id
            WHERE r.fk_muestra_id=?
            ORDER BY p.orden
        """, (mid,)).fetchall()
        return jsonify({"ok": True, "resultados": [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@cal_bp.route("/api/muestras/<int:mid>/resultados", methods=["POST"])
@login_requerido
def api_guardar_resultados(mid):
    data = request.get_json() or {}
    resultados = data.get("resultados", [])
    if not resultados:
        return jsonify({"ok": False, "error": "Sin resultados"}), 400
    conn = get_db()
    try:
        for r in resultados:
            conn.execute("""
                INSERT INTO calidad_resultados
                (fk_muestra_id, fk_param_id, resultado, valor_obtenido, unidad_medida,
                 valor_permitido, observacion, accion_correctiva)
                VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(fk_muestra_id, fk_param_id) DO UPDATE SET
                    resultado=excluded.resultado,
                    valor_obtenido=excluded.valor_obtenido,
                    observacion=excluded.observacion,
                    accion_correctiva=excluded.accion_correctiva,
                    fecha_registro=datetime('now')
            """, (mid,
                  r.get("fk_param_id"),
                  r.get("resultado", "ACEPTABLE"),
                  r.get("valor_obtenido"),
                  r.get("unidad_medida", ""),
                  r.get("valor_permitido", ""),
                  r.get("observacion", ""),
                  r.get("accion_correctiva", "")))
        # Contar no aceptables y actualizar estado muestra
        no_acept = conn.execute(
            "SELECT COUNT(*) FROM calidad_resultados WHERE fk_muestra_id=? AND resultado='NO_ACEPTABLE'",
            (mid,)
        ).fetchone()[0]
        estado = "con_alerta" if no_acept > 0 else "completa"
        conn.execute("UPDATE calidad_muestras SET estado=? WHERE pk_muestra_id=?", (estado, mid))
        conn.commit()
        log_action(accion="UPDATE", modulo="calidad_agua",
                   descripcion=f"Resultados muestra {mid}: {no_acept} no aceptables")
        return jsonify({"ok": True, "no_aceptables": no_acept, "estado": estado})
    except Exception as e:
        conn.rollback()
        _log.error("api_guardar_resultados: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


# ── API: resumen anual ────────────────────────────────────────────────────────

@cal_bp.route("/api/resumen/<int:anio>")
@login_requerido
def api_resumen_anio(anio):
    conn = get_db()
    try:
        muestras = conn.execute(
            "SELECT COUNT(*) as total FROM calidad_muestras WHERE anio=?", (anio,)
        ).fetchone()["total"]
        alertas = conn.execute("""
            SELECT COUNT(*) as total FROM calidad_muestras
            WHERE anio=? AND estado='con_alerta'
        """, (anio,)).fetchone()["total"]
        no_acept = conn.execute("""
            SELECT COUNT(*) as total FROM calidad_resultados r
            JOIN calidad_muestras m ON r.fk_muestra_id=m.pk_muestra_id
            WHERE m.anio=? AND r.resultado='NO_ACEPTABLE'
        """, (anio,)).fetchone()["total"]
        return jsonify({
            "ok": True,
            "anio": anio,
            "muestras": muestras,
            "alertas": alertas,
            "no_aceptables": no_acept,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()
