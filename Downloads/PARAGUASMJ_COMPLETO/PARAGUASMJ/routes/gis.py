"""
routes/gis.py
GIS: Mapa Leaflet offline + APIs GeoJSON.
Mejoras del PROGRAMA.doc:
  - Paginacion en listas (lazy loading)
  - Endpoint de configuracion geografica (lat/lon oficina)
  - Geolocalización del PC como punto de perdida de agua
"""
from flask import Blueprint, render_template, jsonify, request, session
from core.database_manager import get_db
from core.seguridad import login_requerido
import sqlite3, logging

gis_bp = Blueprint("gis", __name__, url_prefix="/gis")
logger = logging.getLogger("asuacap.gis")


@gis_bp.route("/mapa")
@login_requerido
def mapa():
    return render_template("mapa_operaciones.html")


# ── Configuracion geografica (lat/lon oficina y datos del sistema) ──
@gis_bp.route("/api/config")
@login_requerido
def api_config():
    """Retorna la ubicacion de la oficina y configuracion del sistema."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT clave, valor FROM configuracion
            WHERE clave IN (
                'lat_oficina','lon_oficina','nombre_asociacion',
                'direccion_oficina','telefono_oficina','zoom_mapa_inicial'
            )
        """).fetchall()
        cfg = {r["clave"]: r["valor"] for r in rows}
        return jsonify({
            "lat":        float(cfg.get("lat_oficina", 5.0135)),
            "lon":        float(cfg.get("lon_oficina", -74.4700)),
            "zoom":       int(cfg.get("zoom_mapa_inicial", 15)),
            "nombre":     cfg.get("nombre_asociacion", "ASUACAP"),
            "direccion":  cfg.get("direccion_oficina", "Caserio El Puente, Villeta"),
            "telefono":   cfg.get("telefono_oficina", ""),
        })
    except Exception as e:
        logger.error(f"Error config GIS: {e}")
        return jsonify({"lat": 5.0135, "lon": -74.4700, "zoom": 15,
                        "nombre": "ASUACAP", "direccion": "", "telefono": ""})
    finally:
        conn.close()


# ── Infraestructura ─────────────────────────────────────────────────
@gis_bp.route("/api/infraestructura")
@login_requerido
def api_infraestructura():
    conn = get_db()
    features = []
    try:
        rows = conn.execute("""
            SELECT pk_infra_id, nombre, tipo,
                   coordenada_lat, coordenada_lon, estado_operativo, observaciones
            FROM gis_infraestructura
            WHERE coordenada_lat IS NOT NULL AND coordenada_lon IS NOT NULL
        """).fetchall()
        for r in rows:
            features.append({"type": "Feature",
                "geometry": {"type": "Point",
                    "coordinates": [float(r["coordenada_lon"]), float(r["coordenada_lat"])]},
                "properties": {
                    "id": r["pk_infra_id"], "nombre": r["nombre"],
                    "tipo": r["tipo"], "estado": r["estado_operativo"],
                    "observaciones": r["observaciones"] or ""
                }})
    except sqlite3.Error as e:
        logger.error(f"GIS infra: {e}")
    finally:
        conn.close()
    return jsonify({"type": "FeatureCollection", "features": features})


# ── Suscriptores ────────────────────────────────────────────────────
@gis_bp.route("/api/suscriptores")
@login_requerido
def api_suscriptores():
    conn = get_db()
    features = []
    try:
        rows = conn.execute("""
            SELECT s.fk_contacto_id, s.zona_prestacion,
                   s.coordenada_lat, s.coordenada_lon,
                   c.razon_social, s.estado_servicio, s.codigo_medidor
            FROM gis_suscriptores_posicion s
            JOIN contactos c ON s.fk_contacto_id = c.pk_contacto_id
        """).fetchall()
        for r in rows:
            features.append({"type": "Feature",
                "geometry": {"type": "Point",
                    "coordinates": [float(r["coordenada_lon"]), float(r["coordenada_lat"])]},
                "properties": {
                    "id": r["fk_contacto_id"],
                    "nombre": r["razon_social"] or f"Suscriptor {r['fk_contacto_id']}",
                    "zona": r["zona_prestacion"],
                    "medidor": r["codigo_medidor"] or "N/A",
                    "estado": r["estado_servicio"]
                }})
    except sqlite3.Error as e:
        logger.error(f"GIS suscriptores: {e}")
    finally:
        conn.close()
    return jsonify({"type": "FeatureCollection", "features": features})


# ── Fallas ──────────────────────────────────────────────────────────
@gis_bp.route("/api/fallas")
@login_requerido
def api_fallas():
    conn = get_db()
    features = []
    try:
        rows = conn.execute("""
            SELECT pk_falla_id, descripcion_falla, lat_falla, lon_falla,
                   severidad, estado_reparacion, fecha_registro
            FROM gis_reportes_fallas
            WHERE lat_falla IS NOT NULL AND lon_falla IS NOT NULL
        """).fetchall()
        for r in rows:
            features.append({"type": "Feature",
                "geometry": {"type": "Point",
                    "coordinates": [float(r["lon_falla"]), float(r["lat_falla"])]},
                "properties": {
                    "id": r["pk_falla_id"],
                    "descripcion": r["descripcion_falla"],
                    "severidad": r["severidad"],
                    "estado": r["estado_reparacion"],
                    "fecha": r["fecha_registro"]
                }})
    except sqlite3.Error as e:
        logger.error(f"GIS fallas: {e}")
    finally:
        conn.close()
    return jsonify({"type": "FeatureCollection", "features": features})


# ── Nueva falla ─────────────────────────────────────────────────────
@gis_bp.route("/api/fallas/nueva", methods=["POST"])
@login_requerido
def nueva_falla():
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "Sin datos"}), 400
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO gis_reportes_fallas
            (descripcion_falla, lat_falla, lon_falla, severidad, zona_afectada)
            VALUES (?, ?, ?, ?, ?)
        """, (data.get("descripcion", "Falla sin descripcion"),
              float(data["lat"]), float(data["lon"]),
              data.get("severidad", "Media"), data.get("zona_id")))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


# ── Zonas ───────────────────────────────────────────────────────────
@gis_bp.route("/api/zonas")
@login_requerido
def api_zonas():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM zonas_prestacion ORDER BY pk_zona_id").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


# ── API paginada de documentos (lazy loading - PROGRAMA.doc) ────────
@gis_bp.route("/api/documentos_paginados")
@login_requerido
def documentos_paginados():
    """Endpoint paginado para evitar lentitud con cientos de registros."""
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    area     = request.args.get("area", "")
    estado   = request.args.get("estado", "")
    q        = request.args.get("q", "").strip()
    offset   = (page - 1) * per_page

    conn = get_db()
    try:
        sql    = "SELECT pk_registro_id,codigo_completo,asunto_resumen,estado,fecha_radicacion FROM registro_central WHERE 1=1"
        params = []
        if area:
            sql += " AND area=?"; params.append(area)
        if estado:
            sql += " AND estado=?"; params.append(estado)
        if q:
            sql += " AND (codigo_completo LIKE ? OR asunto_resumen LIKE ?)"; params.extend([f"%{q}%"]*2)
        sql += f" ORDER BY pk_registro_id DESC LIMIT {per_page} OFFSET {offset}"
        rows = conn.execute(sql, params).fetchall()
        return jsonify({
            "items":    [dict(r) for r in rows],
            "has_more": len(rows) == per_page,
            "page":     page
        })
    finally:
        conn.close()
