"""
routes/inventarios.py — RC6 GF-05 Inventarios
Control independiente de materiales, equipos, herramientas, químicos, activos.
Entradas, salidas, existencias. Vinculable a órdenes de trabajo.
"""
import logging
from datetime import date
from flask import Blueprint, render_template, request, jsonify, session

from core.database_manager import get_db
from core.seguridad import login_requerido
from utils.audit import log_action

_log = logging.getLogger("sigca.inventarios")

inv_bp = Blueprint("inventarios", __name__, url_prefix="/inventarios")

_CATEGORIAS = ["material", "equipo", "herramienta", "quimico", "activo", "epp", "otro"]


@inv_bp.route("/")
@login_requerido
def panel():
    return render_template("inventarios/panel.html")


# ── API: items ────────────────────────────────────────────────────────────────

@inv_bp.route("/api/items")
@login_requerido
def api_items():
    cat = request.args.get("categoria", "")
    q   = request.args.get("q", "").strip()
    conn = get_db()
    try:
        sql = "SELECT * FROM inventario_items WHERE activo=1"
        params = []
        if cat:
            sql += " AND categoria=?"; params.append(cat)
        if q:
            sql += " AND (nombre LIKE ? OR codigo LIKE ?)"; params.extend([f"%{q}%"]*2)
        sql += " ORDER BY categoria, nombre"
        rows = conn.execute(sql, params).fetchall()
        return jsonify({"ok": True, "items": [dict(r) for r in rows],
                        "categorias": _CATEGORIAS})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@inv_bp.route("/api/items", methods=["POST"])
@login_requerido
def api_crear_item():
    data = request.get_json() or {}
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"ok": False, "error": "Nombre obligatorio"}), 400
    conn = get_db()
    try:
        n = conn.execute("SELECT COUNT(*) FROM inventario_items").fetchone()[0]
        codigo = data.get("codigo") or f"INV-{n+1:05d}"
        conn.execute("""
            INSERT INTO inventario_items
            (codigo, nombre, categoria, unidad, existencia_min, ubicacion)
            VALUES (?,?,?,?,?,?)
        """, (codigo, nombre,
              data.get("categoria", "material"),
              data.get("unidad", "und"),
              data.get("existencia_min", 0),
              data.get("ubicacion", "")))
        conn.commit()
        log_action(accion="CREATE", modulo="inventarios",
                   descripcion=f"Item {codigo} - {nombre} creado")
        return jsonify({"ok": True, "codigo": codigo}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


# ── API: movimientos ──────────────────────────────────────────────────────────

@inv_bp.route("/api/items/<int:item_id>/movimientos")
@login_requerido
def api_movimientos(item_id):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT * FROM inventario_movimientos
            WHERE fk_item_id=? ORDER BY fecha DESC, pk_mov_id DESC LIMIT 100
        """, (item_id,)).fetchall()
        item = conn.execute(
            "SELECT * FROM inventario_items WHERE pk_item_id=?", (item_id,)
        ).fetchone()
        return jsonify({
            "ok": True,
            "item": dict(item) if item else None,
            "movimientos": [dict(r) for r in rows],
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@inv_bp.route("/api/movimiento", methods=["POST"])
@login_requerido
def api_registrar_movimiento():
    data = request.get_json() or {}
    item_id  = data.get("fk_item_id")
    tipo     = data.get("tipo_mov", "").upper()
    cantidad = float(data.get("cantidad") or 0)
    if not item_id or tipo not in ("ENTRADA", "SALIDA", "AJUSTE") or cantidad <= 0:
        return jsonify({"ok": False, "error": "Datos inválidos"}), 400
    conn = get_db()
    try:
        item = conn.execute(
            "SELECT existencia FROM inventario_items WHERE pk_item_id=?", (item_id,)
        ).fetchone()
        if not item:
            return jsonify({"ok": False, "error": "Item no encontrado"}), 404
        existencia = item["existencia"]
        if tipo == "ENTRADA":
            nueva = existencia + cantidad
        elif tipo == "SALIDA":
            if cantidad > existencia:
                return jsonify({"ok": False, "error": "Existencia insuficiente"}), 400
            nueva = existencia - cantidad
        else:  # AJUSTE
            nueva = cantidad

        conn.execute("""
            INSERT INTO inventario_movimientos
            (fk_item_id, tipo_mov, cantidad, existencia_post, fecha, responsable, concepto, fk_ot_id)
            VALUES (?,?,?,?,?,?,?,?)
        """, (item_id, tipo, cantidad, nueva,
              data.get("fecha") or date.today().isoformat(),
              data.get("responsable") or session.get("nombre_usuario", ""),
              data.get("concepto", ""),
              data.get("fk_ot_id")))
        conn.execute(
            "UPDATE inventario_items SET existencia=? WHERE pk_item_id=?",
            (nueva, item_id)
        )
        conn.commit()
        log_action(accion=tipo, modulo="inventarios",
                   descripcion=f"Item {item_id}: {tipo} {cantidad} → existencia {nueva}")
        return jsonify({"ok": True, "existencia_nueva": nueva})
    except Exception as e:
        conn.rollback()
        _log.error("api_registrar_movimiento: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


# ── API: alertas stock mínimo ─────────────────────────────────────────────────

@inv_bp.route("/api/alertas")
@login_requerido
def api_alertas():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT pk_item_id, codigo, nombre, existencia, existencia_min, unidad, categoria
            FROM inventario_items
            WHERE activo=1 AND existencia_min > 0 AND existencia <= existencia_min
            ORDER BY (existencia_min - existencia) DESC
        """).fetchall()
        return jsonify({"ok": True, "alertas": [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()
