"""
routes/gis.py — GIS comunitario PARAGUASMJ v14
"""
from flask import Blueprint, render_template, jsonify, request, session
from core.database_manager import get_db
from core.seguridad import login_requerido
import sqlite3
import logging

gis_bp = Blueprint("gis", __name__, url_prefix="/gis")
logger = logging.getLogger("paraguasmj.gis")


def row_to_geojson_feature(row):
    if "coordenada_lat" in row and "coordenada_lon" in row:
        lat = row.get("coordenada_lat")
        lon = row.get("coordenada_lon")
    elif "lat_falla" in row and "lon_falla" in row:
        lat = row.get("lat_falla")
        lon = row.get("lon_falla")
    else:
        return None

    if lat is None or lon is None:
        return None

    props = {
        "tipo_coordenada":      row.get("tipo_coordenada", "exacta"),
        "sistema":              row.get("sistema_referencia", "WGS84"),
        "utm_x":                row.get("coordenada_utm_x"),
        "utm_y":                row.get("coordenada_utm_y"),
        "zona_utm":             row.get("zona_utm"),
        "precision_metros":     row.get("precision_metros"),
        "fecha_georreferencia": row.get("fecha_georreferencia"),
    }

    if "pk_infra_id" in row:
        props.update({
            "id": row["pk_infra_id"], "nombre": row.get("nombre"),
            "tipo": row.get("tipo"), "estado": row.get("estado_operativo"),
            "observaciones": row.get("observaciones"),
        })
    elif "fk_contacto_id" in row:
        props.update({
            "id": row["fk_contacto_id"],
            "nombre": row.get("razon_social", f"Suscriptor {row['fk_contacto_id']}"),
            "zona": row.get("zona_prestacion"),
            "medidor": row.get("codigo_medidor", "N/A"),
            "estado": row.get("estado_servicio"),
        })
    elif "pk_falla_id" in row:
        props.update({
            "id": row["pk_falla_id"],
            "descripcion": row.get("descripcion_falla"),
            "severidad": row.get("severidad"),
            "estado": row.get("estado_reparacion"),
            "fecha": row.get("fecha_registro"),
        })

    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
        "properties": props,
    }


@gis_bp.route("/mapa")
@login_requerido
def mapa():
    return render_template("mapa_operaciones.html")


@gis_bp.route("/api/config")
@login_requerido
def api_config():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT clave, valor FROM configuracion
            WHERE clave IN (
                'lat_oficina','lon_oficina','nombre_asociacion',
                'nombre_acueducto','direccion_oficina',
                'telefono_oficina','zoom_mapa_inicial'
            )
        """).fetchall()
        cfg = {r["clave"]: r["valor"] for r in rows}
        nombre = cfg.get("nombre_acueducto") or cfg.get("nombre_asociacion", "PARAGUASMJ")
        return jsonify({
            "lat":       float(cfg.get("lat_oficina",  5.0135)),
            "lon":       float(cfg.get("lon_oficina", -74.4700)),
            "zoom":      int(cfg.get("zoom_mapa_inicial", 15)),
            "nombre":    nombre,
            "direccion": cfg.get("direccion_oficina", "Caserio El Puente, Villeta"),
            "telefono":  cfg.get("telefono_oficina", ""),
        })
    except Exception as e:
        logger.error(f"Error config GIS: {e}")
        return jsonify({"lat": 5.0135, "lon": -74.4700, "zoom": 15,
                        "nombre": "PARAGUASMJ", "direccion": "Caserio El Puente", "telefono": ""})
    finally:
        conn.close()


@gis_bp.route("/api/infraestructura")
@login_requerido
def api_infraestructura():
    conn = get_db()
    features = []
    try:
        rows = conn.execute("""
            SELECT * FROM gis_infraestructura
            WHERE coordenada_lat IS NOT NULL AND coordenada_lon IS NOT NULL
        """).fetchall()
        for r in rows:
            feat = row_to_geojson_feature(dict(r))
            if feat:
                features.append(feat)
    except sqlite3.Error as e:
        logger.error(f"GIS infra: {e}")
    finally:
        conn.close()
    return jsonify({"type": "FeatureCollection", "features": features})


@gis_bp.route("/api/suscriptores")
@login_requerido
def api_suscriptores():
    conn = get_db()
    features = []
    try:
        rows = conn.execute("""
            SELECT s.*, c.razon_social
            FROM gis_suscriptores_posicion s
            JOIN contactos c ON s.fk_contacto_id = c.pk_contacto_id
            WHERE s.coordenada_lat IS NOT NULL AND s.coordenada_lon IS NOT NULL
        """).fetchall()
        for r in rows:
            feat = row_to_geojson_feature(dict(r))
            if feat:
                features.append(feat)
    except sqlite3.Error as e:
        logger.error(f"GIS suscriptores: {e}")
    finally:
        conn.close()
    return jsonify({"type": "FeatureCollection", "features": features})


@gis_bp.route("/api/fallas")
@login_requerido
def api_fallas():
    conn = get_db()
    features = []
    try:
        rows = conn.execute("""
            SELECT * FROM gis_reportes_fallas
            WHERE lat_falla IS NOT NULL AND lon_falla IS NOT NULL
        """).fetchall()
        for r in rows:
            feat = row_to_geojson_feature(dict(r))
            if feat:
                features.append(feat)
    except sqlite3.Error as e:
        logger.error(f"GIS fallas: {e}")
    finally:
        conn.close()
    return jsonify({"type": "FeatureCollection", "features": features})


def _mapear_severidad(s):
    mapa = {
        "alta": "Alta_Corte_Servicio",
        "alta_corte_servicio": "Alta_Corte_Servicio",
        "alto": "Alta_Corte_Servicio",
        "media": "Media",
        "medio": "Media",
        "baja": "Baja",
        "bajo": "Baja",
    }
    return mapa.get((s or "media").lower().strip(), "Media")


@gis_bp.route("/api/fallas/nueva", methods=["POST"])
@login_requerido
def nueva_falla():
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "Sin datos"}), 400

    conn = get_db()
    try:
        tipo_coord = data.get("tipo_coordenada", "exacta")
        sistema    = data.get("sistema_referencia", "WGS84")

        precision = data.get("precision_metros")
        if precision is not None:
            try:
                precision = float(precision)
            except (ValueError, TypeError):
                precision = None

        conn.execute("""
            INSERT INTO gis_reportes_fallas
            (descripcion_falla, lat_falla, lon_falla, severidad, zona_afectada,
             tipo_coordenada, sistema_referencia, precision_metros)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("descripcion", "Falla sin descripcion"),
            float(data["lat"]),
            float(data["lon"]),
            _mapear_severidad(data.get("severidad", "Media")),
            data.get("zona_id"),
            tipo_coord,
            sistema,
            precision,
        ))
        conn.commit()
        return jsonify({"ok": True})
    except KeyError as e:
        conn.rollback()
        return jsonify({"ok": False, "error": f"Campo requerido faltante: {e}"}), 400
    except Exception as e:
        conn.rollback()
        logger.error(f"Error registrando falla: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


TIPOS_INFRA = ('Bocatoma','Desarenador','PTAP','Tanque','Tramo','Valvula','Oficina','otro')

@gis_bp.route("/api/infraestructura", methods=["POST"])
@login_requerido
def api_infraestructura_crear():
    data = request.get_json() or {}
    tipo = data.get("tipo", "otro")
    if tipo not in TIPOS_INFRA:
        tipo = "otro"
    conn = get_db()
    try:
        # Ampliar CHECK si es necesario via try/except
        try:
            cur = conn.execute("""
                INSERT INTO gis_infraestructura
                (nombre, tipo, coordenada_lat, coordenada_lon, estado_operativo, observaciones)
                VALUES (?,?,?,?,?,?)
            """, (
                data.get("nombre", "Nuevo punto"), tipo,
                data.get("lat"), data.get("lon"),
                data.get("estado", "Operativo"), data.get("observaciones", "")
            ))
        except Exception:
            cur = conn.execute("""
                INSERT INTO gis_infraestructura
                (nombre, coordenada_lat, coordenada_lon, estado_operativo, observaciones)
                VALUES (?,?,?,?,?)
            """, (
                data.get("nombre", "Nuevo punto"),
                data.get("lat"), data.get("lon"),
                data.get("estado", "Operativo"), data.get("observaciones", "")
            ))
        conn.commit()
        return jsonify({"ok": True, "id": cur.lastrowid}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@gis_bp.route("/api/infraestructura/<int:iid>", methods=["PUT"])
@login_requerido
def api_infraestructura_actualizar(iid):
    data = request.get_json() or {}
    conn = get_db()
    try:
        conn.execute("""
            UPDATE gis_infraestructura
            SET nombre=?, coordenada_lat=?, coordenada_lon=?,
                estado_operativo=?, observaciones=?
            WHERE pk_infra_id=?
        """, (
            data.get("nombre"), data.get("lat"), data.get("lon"),
            data.get("estado", "Operativo"), data.get("observaciones", ""), iid
        ))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@gis_bp.route("/api/infraestructura/<int:iid>", methods=["DELETE"])
@login_requerido
def api_infraestructura_eliminar(iid):
    conn = get_db()
    try:
        conn.execute("DELETE FROM gis_infraestructura WHERE pk_infra_id=?", (iid,))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@gis_bp.route("/api/zonas")
@login_requerido
def api_zonas():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM zonas_prestacion ORDER BY pk_zona_id"
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        logger.error(f"GIS zonas: {e}")
        return jsonify([])
    finally:
        conn.close()


@gis_bp.route("/api/documentos_paginados")
@login_requerido
def documentos_paginados():
    page     = request.args.get("page",     1,  type=int)
    per_page = request.args.get("per_page", 20, type=int)
    area     = request.args.get("area",  "")
    estado   = request.args.get("estado","")
    q        = request.args.get("q",     "").strip()
    offset   = (page - 1) * per_page

    conn = get_db()
    try:
        sql    = ("SELECT pk_registro_id, codigo_completo, asunto_resumen, "
                  "estado, fecha_radicacion FROM registro_central WHERE 1=1")
        params = []
        if area:
            sql += " AND area=?";   params.append(area)
        if estado:
            sql += " AND estado=?"; params.append(estado)
        if q:
            sql += " AND (codigo_completo LIKE ? OR asunto_resumen LIKE ?)"
            params.extend([f"%{q}%"] * 2)
        sql += f" ORDER BY pk_registro_id DESC LIMIT {per_page} OFFSET {offset}"
        rows = conn.execute(sql, params).fetchall()
        return jsonify({
            "items":    [dict(r) for r in rows],
            "has_more": len(rows) == per_page,
            "page":     page,
        })
    except Exception as e:
        logger.error(f"GIS documentos paginados: {e}")
        return jsonify({"items": [], "has_more": False, "page": page})
    finally:
        conn.close()


@gis_bp.route("/api/public/fallas.geojson")
def public_fallas_geojson():
    """GeoJSON sin autenticacion para portales de datos abiertos / IGAC."""
    conn = get_db()
    features = []
    try:
        rows = conn.execute("""
            SELECT descripcion_falla, lat_falla, lon_falla,
                   severidad, estado_reparacion, fecha_registro,
                   tipo_coordenada, sistema_referencia, precision_metros
            FROM gis_reportes_fallas
            WHERE lat_falla IS NOT NULL AND lon_falla IS NOT NULL
              AND estado_reparacion != 'solucionado'
            LIMIT 500
        """).fetchall()
        for r in rows:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(r["lon_falla"]), float(r["lat_falla"])],
                },
                "properties": {
                    "descripcion":      r["descripcion_falla"],
                    "severidad":        r["severidad"],
                    "estado":           r["estado_reparacion"],
                    "fecha":            r["fecha_registro"],
                    "tipo_coordenada":  r["tipo_coordenada"] or "exacta",
                    "sistema":          r["sistema_referencia"] or "WGS84",
                    "precision_metros": r["precision_metros"],
                    "origen":           "PARAGUASMJ - Reporte comunitario acueducto El Puente",
                },
            })
    except sqlite3.Error as e:
        logger.error(f"Error GeoJSON publico: {e}")
    finally:
        conn.close()
    return jsonify({"type": "FeatureCollection", "features": features})
