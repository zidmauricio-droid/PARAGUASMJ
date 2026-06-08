"""
routes/expedientes.py — Gestion de expedientes archivisticos.
Cumple con NTC-ISO 15489 y Ley 594/2000.
"""
from flask import Blueprint, render_template, request, jsonify, abort, Response
from core.database_manager import get_db, db_connection
from core.seguridad import login_requerido
from core.auditoria import auditar
from datetime import datetime
from html import escape

expedientes_bp = Blueprint("expedientes", __name__, url_prefix="/expedientes")


@expedientes_bp.route("/")
@login_requerido
def index():
    return render_template("documentos/expedientes.html")


@expedientes_bp.route("/api/expedientes")
@login_requerido
def api_listar():
    pagina    = request.args.get("pagina",    1,  type=int)
    por_pag   = min(request.args.get("por_pagina", 20, type=int), 100)
    buscar    = request.args.get("buscar",    "").strip()
    estado    = request.args.get("estado",    "")
    fase      = request.args.get("fase",      "")
    offset    = (pagina - 1) * por_pag

    clausulas, params = [], []
    if buscar:
        clausulas.append("(codigo_expediente LIKE ? OR nombre LIKE ?)")
        params += [f"%{buscar}%", f"%{buscar}%"]
    if estado:
        clausulas.append("estado = ?")
        params.append(estado)
    if fase:
        clausulas.append("fase_archivo = ?")
        params.append(fase)

    where = ("WHERE " + " AND ".join(clausulas)) if clausulas else ""

    with db_connection(autocommit=False) as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM expedientes {where}", params
        ).fetchone()[0]

        filas = conn.execute(f"""
            SELECT e.*,
                   (SELECT COUNT(*) FROM registro_central
                    WHERE fk_expediente_id = e.pk_expediente_id) AS total_documentos
            FROM expedientes e
            {where}
            ORDER BY e.pk_expediente_id DESC
            LIMIT ? OFFSET ?
        """, params + [por_pag, offset]).fetchall()

    return jsonify({
        "success":       True,
        "expedientes":   [dict(r) for r in filas],
        "total":         total,
        "pagina":        pagina,
        "total_paginas": max(1, -(-total // por_pag)),
        "desde":         offset + 1 if filas else 0,
        "hasta":         min(offset + por_pag, total),
    })


@expedientes_bp.route("/api/expedientes", methods=["POST"])
@login_requerido
def api_crear():
    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo") or "").strip()
    nombre = (data.get("nombre") or "").strip()

    if not codigo or not nombre:
        return jsonify({"success": False, "error": "Codigo y nombre son obligatorios"}), 400

    with db_connection() as conn:
        if conn.execute(
            "SELECT 1 FROM expedientes WHERE codigo_expediente = ?", (codigo,)
        ).fetchone():
            return jsonify({"success": False, "error": "El codigo ya existe"}), 400

        conn.execute("""
            INSERT INTO expedientes (codigo_expediente, nombre, descripcion, estado, fase_archivo)
            VALUES (?, ?, ?, ?, ?)
        """, (
            codigo,
            nombre,
            (data.get("descripcion") or "").strip(),
            data.get("estado", "Activo"),
            data.get("fase_archivo", "Gestion"),
        ))

    auditar(f"Expediente creado: {codigo} - {nombre}", modulo="expedientes")
    return jsonify({"success": True})


@expedientes_bp.route("/api/expedientes/<int:exp_id>")
@login_requerido
def api_obtener(exp_id):
    with db_connection(autocommit=False) as conn:
        exp = conn.execute(
            "SELECT * FROM expedientes WHERE pk_expediente_id = ?", (exp_id,)
        ).fetchone()
        if not exp:
            return jsonify({"success": False, "error": "No encontrado"}), 404

        docs = conn.execute("""
            SELECT pk_registro_id, codigo_completo, asunto_resumen, fecha_radicacion, estado
            FROM registro_central
            WHERE fk_expediente_id = ?
            ORDER BY fecha_radicacion DESC
        """, (exp_id,)).fetchall()

    return jsonify({
        "success":     True,
        "expediente":  dict(exp),
        "documentos":  [dict(d) for d in docs],
    })


@expedientes_bp.route("/api/expedientes/<int:exp_id>", methods=["PUT"])
@login_requerido
def api_actualizar(exp_id):
    data = request.get_json(silent=True) or {}

    campos_validos = {"nombre", "descripcion", "estado", "fase_archivo"}
    sets, params = [], []
    for campo in campos_validos:
        if campo in data:
            sets.append(f"{campo} = ?")
            params.append(data[campo])

    if not sets:
        return jsonify({"success": False, "error": "Sin campos para actualizar"}), 400

    params.append(exp_id)
    with db_connection() as conn:
        conn.execute(
            f"UPDATE expedientes SET {', '.join(sets)} WHERE pk_expediente_id = ?",
            params,
        )

    auditar(f"Expediente {exp_id} actualizado", modulo="expedientes")
    return jsonify({"success": True})


@expedientes_bp.route("/api/expedientes/<int:exp_id>", methods=["DELETE"])
@login_requerido
def api_eliminar(exp_id):
    with db_connection(autocommit=False) as conn:
        total_docs = conn.execute(
            "SELECT COUNT(*) FROM registro_central WHERE fk_expediente_id = ?", (exp_id,)
        ).fetchone()[0]
        if total_docs:
            return jsonify({
                "success": False,
                "error":   f"No se puede eliminar: tiene {total_docs} documentos asociados",
            }), 400

    with db_connection() as conn:
        conn.execute("DELETE FROM expedientes WHERE pk_expediente_id = ?", (exp_id,))

    auditar(f"Expediente {exp_id} eliminado", modulo="expedientes")
    return jsonify({"success": True})


@expedientes_bp.route("/<int:exp_id>/hoja_control")
@login_requerido
def hoja_control(exp_id):
    with db_connection(autocommit=False) as conn:
        exp = conn.execute(
            "SELECT * FROM expedientes WHERE pk_expediente_id = ?", (exp_id,)
        ).fetchone()
        if not exp:
            abort(404)

        docs = conn.execute("""
            SELECT codigo_completo, asunto_resumen, fecha_radicacion, estado
            FROM registro_central
            WHERE fk_expediente_id = ?
            ORDER BY fecha_radicacion
        """, (exp_id,)).fetchall()

    filas_html = ""
    for i, d in enumerate(docs, 1):
        filas_html += (
            f"<tr><td>{i}</td>"
            f"<td>{escape(d['codigo_completo'])}</td>"
            f"<td>{escape((d['asunto_resumen'] or '')[:60])}</td>"
            f"<td>{d['fecha_radicacion'] or '-'}</td>"
            f"<td>{escape(d['estado'])}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Hoja de Control - {escape(exp['codigo_expediente'])}</title>
<style>
  body{{font-family:Arial,sans-serif;margin:40px;color:#222}}
  h1{{color:#1E3A8A;border-bottom:2px solid #1E3A8A;padding-bottom:.4rem}}
  table{{width:100%;border-collapse:collapse;margin-top:1rem}}
  th,td{{border:1px solid #ccc;padding:7px;text-align:left;font-size:.9rem}}
  th{{background:#1E3A8A;color:#fff}}
  .footer{{margin-top:2rem;font-size:.75rem;text-align:center;color:#666}}
  @media print{{.footer{{position:fixed;bottom:0;width:100%}}}}
</style>
</head>
<body>
<h1>Hoja de Control de Expediente</h1>
<p><strong>Expediente:</strong> {escape(exp['codigo_expediente'])}</p>
<p><strong>Nombre:</strong> {escape(exp['nombre'])}</p>
<p><strong>Estado:</strong> {escape(exp['estado'] or 'Activo')}</p>
<p><strong>Fase:</strong> {escape(exp['fase_archivo'] or 'Gestion')}</p>
<p><strong>Generado:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
<h3>Documentos asociados ({len(docs)})</h3>
<table>
<thead><tr><th>N.</th><th>Codigo</th><th>Asunto</th><th>Fecha</th><th>Estado</th></tr></thead>
<tbody>{filas_html}</tbody>
</table>
<div class="footer">PARAGUASMJ - Sistema de Gestion Documental | Baseline RC5.5</div>
</body>
</html>"""

    return Response(html, mimetype="text/html")
