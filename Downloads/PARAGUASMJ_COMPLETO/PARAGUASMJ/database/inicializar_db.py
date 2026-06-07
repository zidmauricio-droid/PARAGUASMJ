"""
database/inicializar_db.py  -  PARAGUASMJ
Crea las 31 tablas, indices y datos semilla.
Uso: python database/inicializar_db.py
"""
import sqlite3, os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from werkzeug.security import generate_password_hash

DB = Config.DB_PATH

SQL_TABLES = [
# 1 usuarios
"""CREATE TABLE IF NOT EXISTS usuarios (
    pk_usuario_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo TEXT NOT NULL,
    nombre_usuario  TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    rol             TEXT NOT NULL DEFAULT 'auxiliar'
                    CHECK(rol IN('admin','presidente','tesorera','secretaria','auxiliar','tecnico')),
    correo          TEXT,
    telefono        TEXT,
    activo          INTEGER DEFAULT 1,
    ultimo_acceso   TEXT,
    fecha_creacion  TEXT DEFAULT CURRENT_TIMESTAMP
)""",
# 2 contactos
"""CREATE TABLE IF NOT EXISTS contactos (
    pk_contacto_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_interno              TEXT UNIQUE,
    razon_social                TEXT NOT NULL,
    nit_cedula                  TEXT,
    tipo_contacto               TEXT NOT NULL CHECK(tipo_contacto IN
        ('Suscriptor','Proveedor','Entidad','Firmante','Personal')),
    micromedidor_si_no          TEXT CHECK(micromedidor_si_no IN ('SI','NO')),
    activo_desactivo            TEXT DEFAULT 'ACTIVO' CHECK(activo_desactivo IN ('ACTIVO','DESACTIVO')),
    estrato                     INTEGER DEFAULT 1,
    clasificacion               TEXT DEFAULT 'RESIDENCIAL',
    telefono                    TEXT,
    correo                      TEXT,
    direccion_predio            TEXT,
    esquema_datos               TEXT,
    notificacion_tanque         TEXT,
    observacion                 TEXT,
    copia_cedula                TEXT,
    certificado_tradicion       TEXT,
    certificado_estratificacion TEXT,
    declaracion_obligaciones    TEXT,
    tenencia_pozo_septico       TEXT,
    activo                      INTEGER DEFAULT 1,
    fecha_creacion              TEXT DEFAULT CURRENT_TIMESTAMP
)""",
# 3 registro_central
"""CREATE TABLE IF NOT EXISTS registro_central (
    pk_registro_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_completo    TEXT UNIQUE NOT NULL,
    area               TEXT NOT NULL CHECK(area IN('GA','GC','GF','GE','GL')),
    tipo_documento     TEXT NOT NULL,
    anio               INTEGER NOT NULL,
    consecutivo        INTEGER NOT NULL,
    fecha_radicacion   TEXT NOT NULL,
    fecha_vencimiento  TEXT,
    fk_contacto_id     INTEGER,
    asunto_resumen     TEXT NOT NULL,
    notas_internas     TEXT,
    ruta_archivo_docx  TEXT,
    ruta_archivo_pdf   TEXT,
    estado             TEXT DEFAULT 'Borrador' CHECK(estado IN
        ('Borrador','En_revision','En_autorizacion','Aprobado','Rechazado','Archivado')),
    fk_documento_origen_id INTEGER,
    creado_por         TEXT,
    UNIQUE(area, tipo_documento, anio, consecutivo),
    FOREIGN KEY(fk_contacto_id) REFERENCES contactos(pk_contacto_id) ON DELETE SET NULL,
    FOREIGN KEY(fk_documento_origen_id) REFERENCES registro_central(pk_registro_id) ON DELETE SET NULL
)""",
# 4 contenido_documento
"""CREATE TABLE IF NOT EXISTS contenido_documento (
    pk_contenido_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_registro_id  INTEGER NOT NULL UNIQUE,
    contenido_html  TEXT NOT NULL,
    contenido_plain TEXT,
    version         INTEGER DEFAULT 1,
    fecha_edicion   TEXT DEFAULT CURRENT_TIMESTAMP,
    editado_por     TEXT,
    FOREIGN KEY(fk_registro_id) REFERENCES registro_central(pk_registro_id) ON DELETE CASCADE
)""",
# 5 seguimiento_documento
"""CREATE TABLE IF NOT EXISTS seguimiento_documento (
    pk_seg_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_registro_id INTEGER NOT NULL,
    estado_actual  TEXT NOT NULL,
    estado_anterior TEXT,
    fecha_cambio   TEXT DEFAULT CURRENT_TIMESTAMP,
    usuario        TEXT,
    observaciones  TEXT,
    FOREIGN KEY(fk_registro_id) REFERENCES registro_central(pk_registro_id) ON DELETE CASCADE
)""",
# 6 documentos_adjuntos
"""CREATE TABLE IF NOT EXISTS documentos_adjuntos (
    pk_adjunto_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_registro_id INTEGER NOT NULL,
    nombre_archivo TEXT NOT NULL,
    ruta           TEXT NOT NULL,
    tipo_archivo   TEXT,
    tamano_bytes   INTEGER,
    fecha_subida   TEXT DEFAULT CURRENT_TIMESTAMP,
    subido_por     TEXT,
    FOREIGN KEY(fk_registro_id) REFERENCES registro_central(pk_registro_id) ON DELETE CASCADE
)""",
# 7 plazos_documento
"""CREATE TABLE IF NOT EXISTS plazos_documento (
    pk_plazo_id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_registro_id               INTEGER NOT NULL,
    fecha_inicio_notificaciones  TEXT NOT NULL,
    frecuencia_recordatorio      INTEGER DEFAULT 2,
    ultimo_recordatorio          TEXT,
    notificacion_inicial_enviada INTEGER DEFAULT 0,
    FOREIGN KEY(fk_registro_id) REFERENCES registro_central(pk_registro_id) ON DELETE CASCADE
)""",
# 8 firmantes
"""CREATE TABLE IF NOT EXISTS firmantes (
    pk_firmante_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo TEXT NOT NULL,
    cargo           TEXT NOT NULL,
    whatsapp        TEXT NOT NULL UNIQUE,
    correo          TEXT,
    activo          INTEGER DEFAULT 1,
    fecha_inicio    TEXT,
    fecha_fin       TEXT
)""",
# 9 reglas_firmantes
"""CREATE TABLE IF NOT EXISTS reglas_firmantes (
    pk_regla_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_documento TEXT NOT NULL,
    pk_firmante_id INTEGER NOT NULL,
    orden_firma    INTEGER DEFAULT 1,
    obligatorio    INTEGER DEFAULT 1,
    UNIQUE(tipo_documento, pk_firmante_id),
    FOREIGN KEY(pk_firmante_id) REFERENCES firmantes(pk_firmante_id) ON DELETE CASCADE
)""",
# 10 autorizaciones_otp
"""CREATE TABLE IF NOT EXISTS autorizaciones_otp (
    pk_auth_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_registro_id   INTEGER NOT NULL,
    fk_firmante_id   INTEGER NOT NULL,
    codigo_otp       TEXT NOT NULL,
    estado           TEXT DEFAULT 'Enviado' CHECK(estado IN('Enviado','Aprobado','Rechazado','Expirado','Error')),
    fecha_envio      TEXT DEFAULT CURRENT_TIMESTAMP,
    fecha_expiracion TEXT NOT NULL,
    fecha_aprobacion TEXT,
    intentos_envio   INTEGER DEFAULT 0,
    ultimo_error     TEXT,
    FOREIGN KEY(fk_registro_id) REFERENCES registro_central(pk_registro_id) ON DELETE CASCADE,
    FOREIGN KEY(fk_firmante_id) REFERENCES firmantes(pk_firmante_id)
)""",
# 11 acciones_pendientes
"""CREATE TABLE IF NOT EXISTS acciones_pendientes (
    pk_accion_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_registro_id  INTEGER NOT NULL,
    tipo_accion     TEXT NOT NULL CHECK(tipo_accion IN('revisar','autorizar','responder')),
    responsable_id  INTEGER NOT NULL,
    fecha_limite    TEXT NOT NULL,
    fecha_completado TEXT,
    estado          TEXT DEFAULT 'Pendiente' CHECK(estado IN('Pendiente','Completada','Cancelada')),
    observacion     TEXT,
    FOREIGN KEY(fk_registro_id) REFERENCES registro_central(pk_registro_id) ON DELETE CASCADE,
    FOREIGN KEY(responsable_id) REFERENCES firmantes(pk_firmante_id)
)""",
# 12 pqrs
"""CREATE TABLE IF NOT EXISTS pqrs (
    pk_pqr_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_registro_id        INTEGER UNIQUE NOT NULL,
    tipo_pqr              TEXT NOT NULL CHECK(tipo_pqr IN('Peticion','Queja','Reclamo','Sugerencia','Denuncia','Consulta','Recurso de Reposicion','Recurso de Apelacion')),
    fk_suscriptor_id      INTEGER NOT NULL,
    medio_recepcion       TEXT NOT NULL,
    estado_pqr            TEXT DEFAULT 'Recibida' CHECK(estado_pqr IN('Recibida','En_tramite','Respondida','Cerrada')),
    fecha_limite          TEXT NOT NULL,
    descripcion_detallada TEXT,
    respuesta_definitiva  TEXT,
    fk_oficio_respuesta_id INTEGER,
    fecha_respuesta       TEXT,
    FOREIGN KEY(fk_registro_id) REFERENCES registro_central(pk_registro_id) ON DELETE CASCADE,
    FOREIGN KEY(fk_suscriptor_id) REFERENCES contactos(pk_contacto_id),
    FOREIGN KEY(fk_oficio_respuesta_id) REFERENCES registro_central(pk_registro_id)
)""",
# 13 comunicaciones_recibidas
"""CREATE TABLE IF NOT EXISTS comunicaciones_recibidas (
    pk_com_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_registro_id     INTEGER,
    entidad_remitente  TEXT NOT NULL,
    radicado_externo   TEXT,
    asunto             TEXT NOT NULL,
    fecha_recepcion    TEXT NOT NULL,
    requiere_respuesta INTEGER DEFAULT 0,
    fecha_limite_resp  TEXT,
    estado             TEXT DEFAULT 'Pendiente',
    observaciones      TEXT,
    FOREIGN KEY(fk_registro_id) REFERENCES registro_central(pk_registro_id) ON DELETE SET NULL
)""",
# 14 proyectos
"""CREATE TABLE IF NOT EXISTS proyectos (
    pk_proyecto_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo                TEXT UNIQUE NOT NULL,
    nombre                TEXT NOT NULL,
    descripcion           TEXT,
    departamento          TEXT,
    responsable_id        INTEGER,
    presupuesto           REAL DEFAULT 0,
    valor_ejecutado       REAL DEFAULT 0,
    fecha_inicio          TEXT,
    fecha_limite          TEXT,
    fecha_real_fin        TEXT,
    porcentaje_completado REAL DEFAULT 0,
    estado                TEXT DEFAULT 'En Proceso',
    performance           REAL DEFAULT 0,
    comentarios           TEXT,
    fecha_creacion        TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(responsable_id) REFERENCES contactos(pk_contacto_id)
)""",
# 15 actividades
"""CREATE TABLE IF NOT EXISTS actividades (
    pk_actividad_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_proyecto_id  INTEGER NOT NULL,
    codigo          TEXT NOT NULL,
    nombre          TEXT NOT NULL,
    tipo            TEXT DEFAULT 'Actividad',
    responsable     TEXT,
    fecha_inicio    TEXT,
    fecha_limite    TEXT,
    fecha_real_fin  TEXT,
    porcentaje      REAL DEFAULT 0,
    estado          TEXT DEFAULT 'Pendiente',
    FOREIGN KEY(fk_proyecto_id) REFERENCES proyectos(pk_proyecto_id) ON DELETE CASCADE
)""",
# 16 presupuesto_rubros
"""CREATE TABLE IF NOT EXISTS presupuesto_rubros (
    pk_rubro_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    anio               INTEGER NOT NULL,
    nombre_rubro       TEXT NOT NULL,
    presupuesto_inicial REAL DEFAULT 0,
    comprometido       REAL DEFAULT 0,
    ejecutado          REAL DEFAULT 0,
    UNIQUE(anio, nombre_rubro)
)""",
# 17 cotizaciones
"""CREATE TABLE IF NOT EXISTS cotizaciones (
    pk_cotizacion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_registro_id   INTEGER,
    fk_proveedor_id  INTEGER NOT NULL,
    total            REAL DEFAULT 0,
    fecha_validez    TEXT,
    estado           TEXT DEFAULT 'Registrada',
    observaciones    TEXT,
    FOREIGN KEY(fk_registro_id) REFERENCES registro_central(pk_registro_id) ON DELETE SET NULL,
    FOREIGN KEY(fk_proveedor_id) REFERENCES contactos(pk_contacto_id)
)""",
# 18 ordenes_compra_productos
"""CREATE TABLE IF NOT EXISTS ordenes_compra_productos (
    pk_detalle_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_registro_id  INTEGER NOT NULL,
    descripcion     TEXT NOT NULL,
    unidad          TEXT DEFAULT 'und',
    cantidad        REAL NOT NULL,
    precio_unitario REAL NOT NULL,
    subtotal        REAL NOT NULL,
    iva_porcentaje  REAL DEFAULT 19,
    fk_rubro_id     INTEGER,
    FOREIGN KEY(fk_registro_id) REFERENCES registro_central(pk_registro_id) ON DELETE CASCADE,
    FOREIGN KEY(fk_rubro_id) REFERENCES presupuesto_rubros(pk_rubro_id)
)""",
# 19 tareas
"""CREATE TABLE IF NOT EXISTS tareas (
    pk_tarea_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo           TEXT NOT NULL,
    descripcion      TEXT,
    fecha_programada TEXT NOT NULL,
    hora_programada  TEXT,
    duracion_minutos INTEGER DEFAULT 60,
    prioridad        TEXT DEFAULT 'Media' CHECK(prioridad IN('Alta','Media','Baja')),
    estado_tarea     TEXT DEFAULT 'Pendiente',
    fk_registro_id   INTEGER,
    asignado_a       TEXT,
    recurrencia      TEXT DEFAULT 'Ninguna',
    color_evento     TEXT DEFAULT '#3b82f6',
    fecha_completado TEXT,
    FOREIGN KEY(fk_registro_id) REFERENCES registro_central(pk_registro_id) ON DELETE SET NULL
)""",
# 20 ordenes_trabajo
"""CREATE TABLE IF NOT EXISTS ordenes_trabajo (
    pk_ot_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_registro_id       INTEGER UNIQUE NOT NULL,
    tipo_servicio        TEXT DEFAULT 'Acueducto' CHECK(tipo_servicio IN('Acueducto','Alcantarillado','Mixto')),
    fecha_ejecucion      TEXT NOT NULL,
    hora_inicio          TEXT,
    lugar                TEXT,
    responsable_tecnico  TEXT,
    supervisor           TEXT,
    descripcion_tareas   TEXT,
    epp_requeridos       TEXT,
    observaciones        TEXT,
    estado_ot            TEXT DEFAULT 'Pendiente',
    FOREIGN KEY(fk_registro_id) REFERENCES registro_central(pk_registro_id) ON DELETE CASCADE
)""",
# 21 ordenes_salida
"""CREATE TABLE IF NOT EXISTS ordenes_salida (
    pk_os_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_ot_id           INTEGER NOT NULL,
    fecha_salida       TEXT NOT NULL,
    hora_salida        TEXT,
    lugar_destino      TEXT,
    personal_asignado  TEXT,
    vehiculo_placa     TEXT,
    kilometraje_salida INTEGER,
    kilometraje_regreso INTEGER,
    latitud            REAL,
    longitud           REAL,
    estado_salida      TEXT DEFAULT 'Programada',
    FOREIGN KEY(fk_ot_id) REFERENCES ordenes_trabajo(pk_ot_id) ON DELETE CASCADE
)""",
# 22 actas_ejecucion
"""CREATE TABLE IF NOT EXISTS actas_ejecucion (
    pk_ae_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_ot_id              INTEGER NOT NULL,
    fecha_ejecucion       TEXT NOT NULL,
    hora_inicio           TEXT,
    hora_fin              TEXT,
    tareas_realizadas     TEXT,
    materiales_utilizados TEXT,
    fotos_rutas           TEXT,
    observaciones         TEXT,
    novedades             TEXT,
    estado_acta           TEXT DEFAULT 'Borrador',
    firma_tecnico         TEXT,
    firma_supervisor      TEXT,
    FOREIGN KEY(fk_ot_id) REFERENCES ordenes_trabajo(pk_ot_id) ON DELETE CASCADE
)""",
# 23 lecturas_macromedicion
"""CREATE TABLE IF NOT EXISTS lecturas_macromedicion (
    pk_lectura_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha            TEXT NOT NULL UNIQUE,
    lectura_inicial  REAL,
    lectura_final    REAL,
    produccion_diaria REAL,
    observaciones    TEXT
)""",
# 24 balance_hidrico
"""CREATE TABLE IF NOT EXISTS balance_hidrico (
    pk_balance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    anio          INTEGER NOT NULL,
    mes           INTEGER NOT NULL,
    produccion_m3 REAL DEFAULT 0,
    facturado_m3  REAL DEFAULT 0,
    perdidas_m3   REAL DEFAULT 0,
    observaciones TEXT,
    UNIQUE(anio, mes)
)""",
# 25 indicadores_mensuales
"""CREATE TABLE IF NOT EXISTS indicadores_mensuales (
    pk_ind_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    anio          INTEGER NOT NULL,
    mes           INTEGER NOT NULL,
    produccion_m3 REAL,
    facturado_m3  REAL,
    perdidas_m3   REAL,
    ianc          REAL,
    ipaa          REAL,
    ima           REAL,
    poac          REAL,
    irac          REAL,
    UNIQUE(anio, mes)
)""",
# 26 riesgos
"""CREATE TABLE IF NOT EXISTS riesgos (
    pk_riesgo_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo               TEXT UNIQUE NOT NULL,
    nombre               TEXT NOT NULL,
    fecha_identificacion TEXT,
    tipo_amenaza         TEXT CHECK(tipo_amenaza IN('Amenaza','Oportunidad')),
    categoria            TEXT,
    probabilidad         REAL,
    impacto_alcance      REAL,
    impacto_tiempo       REAL,
    impacto_costo        REAL,
    impacto_calidad      REAL,
    valoracion_global    REAL,
    prioridad            TEXT CHECK(prioridad IN('Alta','Media','Baja')),
    dueno                TEXT,
    responsable          TEXT,
    plan_respuesta       TEXT,
    activado             INTEGER DEFAULT 0,
    fecha_activacion     TEXT,
    justificacion        TEXT
)""",
# 27 bancos
"""CREATE TABLE IF NOT EXISTS bancos (
    pk_banco_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_cuenta TEXT UNIQUE NOT NULL,
    banco_nombre  TEXT NOT NULL,
    tipo_cuenta   TEXT,
    moneda        TEXT DEFAULT 'COP',
    saldo_actual  REAL DEFAULT 0,
    ejecutivo     TEXT,
    telefono      TEXT,
    status        TEXT DEFAULT 'ACTIVA'
)""",
# 28 movimientos_financieros
"""CREATE TABLE IF NOT EXISTS movimientos_financieros (
    pk_mov_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha          TEXT NOT NULL,
    fk_banco_id    INTEGER,
    tipo_mov       TEXT NOT NULL CHECK(tipo_mov IN('INGRESO','EGRESO')),
    concepto       TEXT NOT NULL,
    importe        REAL NOT NULL,
    referencia     TEXT,
    usuario        TEXT,
    fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(fk_banco_id) REFERENCES bancos(pk_banco_id) ON DELETE SET NULL
)""",
# 29 caja_chica
"""CREATE TABLE IF NOT EXISTS caja_chica (
    pk_caja_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha          TEXT NOT NULL,
    concepto       TEXT NOT NULL,
    tipo_mov       TEXT NOT NULL CHECK(tipo_mov IN('INGRESO','EGRESO')),
    importe        REAL NOT NULL,
    usuario        TEXT,
    fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP
)""",
# 30 GIS
"""CREATE TABLE IF NOT EXISTS zonas_prestacion (
    pk_zona_id  INTEGER PRIMARY KEY,
    nombre_zona TEXT NOT NULL,
    descripcion TEXT
)""",
"""CREATE TABLE IF NOT EXISTS gis_infraestructura (
    pk_infra_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre           TEXT NOT NULL,
    tipo             TEXT CHECK(tipo IN('Bocatoma','Desarenador','PTAP','Tanque','Tramo')),
    coordenada_lat   REAL,
    coordenada_lon   REAL,
    geojson_linea    TEXT,
    estado_operativo TEXT DEFAULT 'Operativo',
    observaciones    TEXT,
    zona_id          INTEGER,
    FOREIGN KEY(zona_id) REFERENCES zonas_prestacion(pk_zona_id)
)""",
"""CREATE TABLE IF NOT EXISTS gis_suscriptores_posicion (
    fk_contacto_id  INTEGER PRIMARY KEY,
    zona_prestacion INTEGER NOT NULL,
    coordenada_lat  REAL NOT NULL,
    coordenada_lon  REAL NOT NULL,
    codigo_medidor  TEXT,
    estado_servicio TEXT DEFAULT 'Activo',
    FOREIGN KEY(fk_contacto_id) REFERENCES contactos(pk_contacto_id) ON DELETE CASCADE,
    FOREIGN KEY(zona_prestacion) REFERENCES zonas_prestacion(pk_zona_id)
)""",
"""CREATE TABLE IF NOT EXISTS gis_reportes_fallas (
    pk_falla_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_infra_id       INTEGER,
    descripcion_falla TEXT NOT NULL,
    zona_afectada     INTEGER,
    lat_falla         REAL NOT NULL,
    lon_falla         REAL NOT NULL,
    severidad         TEXT CHECK(severidad IN('Baja','Media','Alta_Corte_Servicio')),
    estado_reparacion TEXT DEFAULT 'Pendiente',
    fecha_registro    TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(fk_infra_id) REFERENCES gis_infraestructura(pk_infra_id),
    FOREIGN KEY(zona_afectada) REFERENCES zonas_prestacion(pk_zona_id)
)""",
# 31 configuracion
"""CREATE TABLE IF NOT EXISTS configuracion (
    clave                       TEXT PRIMARY KEY,
    valor                       TEXT NOT NULL,
    descripcion                 TEXT,
    categoria                   TEXT NOT NULL DEFAULT 'General',
    tipo_dato                   TEXT DEFAULT 'texto',
    modulo                      TEXT,
    orden                       INTEGER DEFAULT 0,
    editable_por                TEXT DEFAULT 'admin',
    fecha_actualizacion         TEXT DEFAULT CURRENT_TIMESTAMP,
    usuario_ultima_modificacion TEXT
)""",
"""CREATE TABLE IF NOT EXISTS configuracion_historial (
    pk_hist_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    clave          TEXT NOT NULL,
    valor_anterior TEXT,
    valor_nuevo    TEXT,
    fecha_cambio   TEXT DEFAULT CURRENT_TIMESTAMP,
    usuario        TEXT,
    motivo         TEXT
)""",
# Auxiliares
"""CREATE TABLE IF NOT EXISTS control_consecutivos (
    area           TEXT NOT NULL,
    tipo_documento TEXT NOT NULL,
    anio           INTEGER NOT NULL,
    ultimo         INTEGER DEFAULT 0,
    PRIMARY KEY(area, tipo_documento, anio)
)""",
"""CREATE TABLE IF NOT EXISTS notificaciones_historial (
    pk_hist_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_envio  TEXT DEFAULT CURRENT_TIMESTAMP,
    destinatario TEXT,
    canal        TEXT,
    mensaje      TEXT,
    estado_envio TEXT,
    error_mensaje TEXT
)""",
"""CREATE TABLE IF NOT EXISTS logs_sistema (
    pk_log_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha      TEXT DEFAULT CURRENT_TIMESTAMP,
    nivel      TEXT,
    modulo     TEXT,
    usuario    TEXT,
    accion     TEXT,
    detalle    TEXT,
    ip_origen  TEXT
)""",
"""CREATE TABLE IF NOT EXISTS sesiones_log (
    pk_sesion_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    fk_usuario_id INTEGER,
    fecha_inicio  TEXT DEFAULT CURRENT_TIMESTAMP,
    fecha_fin     TEXT,
    ip_origen     TEXT,
    user_agent    TEXT
)""",
]

INDICES = [
"CREATE INDEX IF NOT EXISTS idx_reg_codigo ON registro_central(codigo_completo)",
"CREATE INDEX IF NOT EXISTS idx_reg_estado ON registro_central(estado)",
"CREATE INDEX IF NOT EXISTS idx_reg_area ON registro_central(area,tipo_documento,anio)",
"CREATE INDEX IF NOT EXISTS idx_reg_fecha ON registro_central(fecha_radicacion)",
"CREATE INDEX IF NOT EXISTS idx_contactos_codigo ON contactos(codigo_interno)",
"CREATE INDEX IF NOT EXISTS idx_contactos_razon ON contactos(razon_social)",
"CREATE INDEX IF NOT EXISTS idx_contactos_tipo ON contactos(tipo_contacto)",
"CREATE INDEX IF NOT EXISTS idx_otp_reg ON autorizaciones_otp(fk_registro_id)",
"CREATE INDEX IF NOT EXISTS idx_plazos_reg ON plazos_documento(fk_registro_id)",
"CREATE INDEX IF NOT EXISTS idx_acc_estado ON acciones_pendientes(estado,fecha_limite)",
"CREATE INDEX IF NOT EXISTS idx_tareas_fecha ON tareas(fecha_programada)",
"CREATE INDEX IF NOT EXISTS idx_lecturas_fecha ON lecturas_macromedicion(fecha)",
"CREATE INDEX IF NOT EXISTS idx_pqrs_estado ON pqrs(estado_pqr)",
"CREATE INDEX IF NOT EXISTS idx_logs_fecha ON logs_sistema(fecha)",
"CREATE INDEX IF NOT EXISTS idx_config_cat ON configuracion(categoria)",
]

def inicializar_base_datos():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA journal_mode=WAL")
    print("="*60)
    print("  PARAGUASMJ — Inicializando base de datos")
    print("="*60)
    for sql in SQL_TABLES:
        c.execute(sql)
    for idx in INDICES:
        c.execute(idx)

    try:
        from werkzeug.security import generate_password_hash as gph
        hp = gph("PARAGUASMJ2026")
    except ImportError:
        import hashlib
        hp = "pbkdf2:sha256:$" + hashlib.sha256(b"PARAGUASMJ2026").hexdigest()

    c.execute("INSERT OR IGNORE INTO usuarios(nombre_completo,nombre_usuario,password_hash,rol) VALUES(?,?,?,?)",
              ("Administrador del Sistema","admin",hp,"admin"))

    zonas = [(1,"La Volconda","Critica: tuberias 3/8\""),(2,"Payande - Tres Esquinas","Zona residencial dispersa"),
             (3,"Alto de Torres - Bajo","Problemas de presion"),(4,"Caserio El Puente","Centro poblado"),
             (5,"El Penon - La Masata","Extremo norte")]
    c.executemany("INSERT OR IGNORE INTO zonas_prestacion VALUES(?,?,?)", zonas)

    infra = [(1,"Bocatoma Rio Negro","Bocatoma",5.0160,-74.4720,"Operativo",4),
             (2,"Desarenador PTAP","Desarenador",5.0145,-74.4700,"Falla Critica",4),
             (3,"Planta PTAP","PTAP",5.0130,-74.4690,"Operativo",4),
             (4,"Tanque Principal","Tanque",5.0120,-74.4680,"Operativo",4)]
    c.executemany("INSERT OR IGNORE INTO gis_infraestructura(pk_infra_id,nombre,tipo,coordenada_lat,coordenada_lon,estado_operativo,zona_id) VALUES(?,?,?,?,?,?,?)", infra)

    firm = [("Jose Humberto Ramirez","Presidente","+573001234567"),
            ("Ana Martinez Garcia","Tesorera","+573002345678"),
            ("Maria Lopez Ruiz","Secretaria","+573003456789"),
            ("Luis Gomez Castro","Comite Juridico","+573004567890")]
    c.executemany("INSERT OR IGNORE INTO firmantes(nombre_completo,cargo,whatsapp,activo) VALUES(?,?,?,1)", firm)

    c.execute("SELECT pk_firmante_id,cargo FROM firmantes")
    fm = {r[1]:r[0] for r in c.fetchall()}
    reglas = [("OFI",fm.get("Presidente",1),1,1),("ACT",fm.get("Presidente",1),1,1),
              ("ACT",fm.get("Secretaria",3),2,1),("OC",fm.get("Presidente",1),1,1),
              ("OC",fm.get("Tesorera",2),2,1),("RES",fm.get("Presidente",1),1,1),
              ("RES",fm.get("Secretaria",3),2,1),("PQR",fm.get("Secretaria",3),1,1),
              ("OT",fm.get("Presidente",1),1,1),("COT",fm.get("Presidente",1),1,1),
              ("COT",fm.get("Tesorera",2),2,1)]
    c.executemany("INSERT OR IGNORE INTO reglas_firmantes(tipo_documento,pk_firmante_id,orden_firma,obligatorio) VALUES(?,?,?,?)", reglas)

    anio = datetime.now().year
    rubros = ["Mantenimiento Redes","Personal","Quimicos","Estudios Tecnicos","Tasas CAR","Gastos Administrativos","Inversiones"]
    c.executemany("INSERT OR IGNORE INTO presupuesto_rubros(anio,nombre_rubro,presupuesto_inicial) VALUES(?,?,0)", [(anio,r) for r in rubros])

    configs = [
        ("nombre_asociacion","ASUACAP","Nombre oficial","Institucional","texto",None,1),
        ("nombre_completo","Asociacion de Suscriptores del Acueducto Comunitario El Puente","Nombre completo","Institucional","texto",None,2),
        ("nit","8320013892","NIT","Institucional","texto",None,3),
        ("representante_legal","Jose Humberto Ramirez","Representante","Institucional","texto",None,4),
        ("cargo_representante","Presidente","Cargo","Institucional","texto",None,5),
        ("direccion_oficina","Caserio El Puente, Villeta Cundinamarca","Direccion","Institucional","texto",None,6),
        ("telefono_oficina","3112345678","Telefono","Institucional","texto",None,7),
        ("correo_oficial","aacueductoelpuente@yahoo.com","Correo","Institucional","texto",None,8),
        ("codigo_departamento","25","DIVIPOLA Cundinamarca","Institucional","texto",None,9),
        ("codigo_municipio","258","DIVIPOLA Villeta","Institucional","texto",None,10),
        ("ianc_umbral_verde","15","IANC bueno %","Tecnica","numero","balance",1),
        ("ianc_umbral_naranja","25","IANC riesgo %","Tecnica","numero","balance",2),
        ("presion_minima_psi","20","Presion minima PSI","Tecnica","numero",None,3),
        ("dotacion_neta_lpcd","120","L/persona/dia","Tecnica","numero",None,4),
        ("personas_por_suscriptor","4","Habitantes/vivienda","Tecnica","numero",None,5),
        ("plazo_respuesta_pqrs","15","Dias habiles PQRS","Tecnica","numero","pqrs",6),
        ("dias_alerta_documentos","4","Dias inicio alertas doc","Tecnica","numero",None,7),
        ("dias_plazo_autorizacion","7","Dias autorizar","Tecnica","numero",None,8),
        ("whatsapp_api_key","","API Key CallMeBot","Notificaciones","texto","comunicaciones",1),
        ("whatsapp_numero_oficial","573001234567","WhatsApp ASUACAP","Notificaciones","texto","comunicaciones",2),
        ("email_smtp_host","smtp.gmail.com","Servidor SMTP","Notificaciones","texto","comunicaciones",3),
        ("email_smtp_port","587","Puerto SMTP","Notificaciones","texto","comunicaciones",4),
        ("email_usuario","","Correo remitente","Notificaciones","texto","comunicaciones",5),
        ("email_password","","Contrasena correo","Notificaciones","texto","comunicaciones",6),
        ("notificar_vencimientos","1","Enviar alertas (1=Si)","Notificaciones","booleano",None,7),
        ("modulo_pqrs_activo","1","Activar PQRS","Modulos","booleano","pqrs",1),
        ("modulo_proyectos_activo","1","Activar proyectos","Modulos","booleano","proyectos",2),
        ("modulo_balance_activo","1","Activar balance hidrico","Modulos","booleano","balance",3),
        ("modulo_gis_activo","1","Activar GIS","Modulos","booleano","gis",4),
        ("modulo_finanzas_activo","1","Activar finanzas","Modulos","booleano","finanzas",5),
    ]
    c.executemany("INSERT OR IGNORE INTO configuracion(clave,valor,descripcion,categoria,tipo_dato,modulo,orden) VALUES(?,?,?,?,?,?,?)", configs)

    # ── Columnas y tablas agregadas en versiones posteriores ────────
    _alters = [
        ("pqrs", "radicado_visible",        "TEXT"),
        ("pqrs", "resumen",                 "TEXT"),
        ("pqrs", "componente_afectado",     "TEXT"),
        ("pqrs", "requiere_visita",         "INTEGER DEFAULT 0"),
        ("pqrs", "notificado_usuario",      "INTEGER DEFAULT 0"),
        ("pqrs", "conformidad_usuario",     "INTEGER DEFAULT 0"),
        ("pqrs", "canal_codigo",            "TEXT DEFAULT '99'"),
        ("pqrs", "causal_codigo",           "TEXT DEFAULT '99'"),
        ("pqrs", "causal_texto",            "TEXT"),
        ("pqrs", "subcausal_codigo",        "TEXT"),
        ("pqrs", "subcausal_texto",         "TEXT"),
        ("pqrs", "servicio_codigo",         "TEXT DEFAULT '1'"),
        ("pqrs", "en_segunda_instancia",    "INTEGER DEFAULT 0"),
        ("pqrs", "fecha_recurso",           "TEXT"),
        ("pqrs", "tipo_recurso",            "TEXT"),
        ("pqrs", "fecha_respuesta_real",    "TEXT"),
        ("pqrs", "reportado_sui",           "INTEGER DEFAULT 0"),
        ("pqrs", "mes_reporte",             "TEXT"),
        ("ordenes_trabajo", "pqrs_id",              "INTEGER"),
        ("ordenes_trabajo", "numero_orden",          "TEXT"),
        ("ordenes_trabajo", "tecnico_asignado",      "TEXT"),
        ("ordenes_trabajo", "materiales",            "TEXT"),
        ("ordenes_trabajo", "fecha_estimada",        "TEXT"),
        ("ordenes_trabajo", "aceptada_tecnico",      "INTEGER DEFAULT 0"),
        ("ordenes_trabajo", "prioridad",             "TEXT DEFAULT 'normal'"),
        ("actas_ejecucion", "pruebas_presion",       "TEXT"),
        ("actas_ejecucion", "pruebas_cloro",         "TEXT"),
        ("actas_ejecucion", "conformidad_usuario",   "INTEGER DEFAULT 0"),
        ("actas_ejecucion", "verificado_supervisor", "INTEGER DEFAULT 0"),
        ("actas_ejecucion", "fecha_verificacion",    "TEXT"),
        ("balance_hidrico", "bocatoma_m3",           "REAL"),
        ("balance_hidrico", "entrada_ptap_m3",       "REAL"),
        ("balance_hidrico", "salida_ptap_m3",        "REAL"),
        ("balance_hidrico", "consumo_facturado_m3",  "REAL"),
        ("balance_hidrico", "fallas_aduccion",       "INTEGER DEFAULT 0"),
        ("balance_hidrico", "longitud_aduccion_km",  "REAL"),
        ("balance_hidrico", "fallas_distribucion",   "INTEGER DEFAULT 0"),
        ("balance_hidrico", "longitud_distribucion_km", "REAL"),
        ("balance_hidrico", "suscriptores",          "INTEGER DEFAULT 0"),
        ("balance_hidrico", "empleados",             "INTEGER DEFAULT 0"),
        ("balance_hidrico", "micromedidores_instalados", "INTEGER DEFAULT 0"),
        ("balance_hidrico", "micromedidores_efectivos",  "INTEGER DEFAULT 0"),
        ("balance_hidrico", "ianc_pct",              "REAL"),
        ("balance_hidrico", "ipuf_m3_susc_mes",      "REAL"),
        ("balance_hidrico", "ima",                   "REAL"),
    ]
    for _tb, _col, _tipo in _alters:
        try:
            conn.execute(f"ALTER TABLE {_tb} ADD COLUMN {_col} {_tipo}")
        except Exception:
            pass
    conn.execute("""CREATE TABLE IF NOT EXISTS autorizadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL, cargo TEXT NOT NULL,
        telefono TEXT, email TEXT, activo INTEGER DEFAULT 1,
        orden_firma INTEGER DEFAULT 1, tipo TEXT DEFAULT 'junta',
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS lecturas_macromedidor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL, punto TEXT NOT NULL,
        lectura_m3 REAL NOT NULL, caudal_lps REAL,
        turbiedad_ntu REAL, cloro_mg_l REAL,
        observaciones TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lmm_fecha ON lecturas_macromedidor(fecha)")
    except Exception:
        pass
    conn.execute("""CREATE TABLE IF NOT EXISTS tareas_proyecto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proyecto_id INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        prioridad TEXT DEFAULT 'media',
        estado TEXT DEFAULT 'pendiente',
        fecha_inicio_plan TEXT,
        fecha_fin_plan TEXT,
        fecha_inicio_real TEXT,
        fecha_fin_real TEXT,
        porcentaje_avance INTEGER DEFAULT 0,
        responsable_id INTEGER,
        costo_estimado REAL DEFAULT 0,
        costo_real REAL DEFAULT 0,
        orden INTEGER DEFAULT 0,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(proyecto_id) REFERENCES proyectos(pk_proyecto_id) ON DELETE CASCADE
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tp_proy ON tareas_proyecto(proyecto_id)")
    conn.execute("""CREATE TABLE IF NOT EXISTS riesgos_proyecto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pk_riesgo_id INTEGER,
        proyecto_id INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        probabilidad INTEGER DEFAULT 1,
        impacto INTEGER DEFAULT 1,
        categoria TEXT,
        plan_mitigacion TEXT,
        estado TEXT DEFAULT 'identificado',
        FOREIGN KEY(proyecto_id) REFERENCES proyectos(pk_proyecto_id)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS documentos_proyecto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proyecto_id INTEGER NOT NULL,
        documento_id INTEGER,
        nombre_archivo TEXT,
        descripcion TEXT,
        tipo_relacion TEXT DEFAULT 'soporte',
        subido_por INTEGER,
        fecha_subida TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(proyecto_id) REFERENCES proyectos(pk_proyecto_id)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS costos_proyecto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proyecto_id INTEGER NOT NULL,
        concepto TEXT NOT NULL,
        valor REAL NOT NULL DEFAULT 0,
        fecha TEXT NOT NULL,
        categoria TEXT,
        comprobante TEXT,
        registrado_por INTEGER,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(proyecto_id) REFERENCES proyectos(pk_proyecto_id)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS ingresos_proyecto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proyecto_id INTEGER NOT NULL,
        concepto TEXT NOT NULL,
        valor REAL NOT NULL DEFAULT 0,
        fecha TEXT NOT NULL,
        fuente TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(proyecto_id) REFERENCES proyectos(pk_proyecto_id)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS evidencias_proyecto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proyecto_id INTEGER NOT NULL,
        nombre_archivo TEXT NOT NULL,
        ruta TEXT NOT NULL,
        descripcion TEXT,
        subido_por INTEGER,
        fecha_subida TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(proyecto_id) REFERENCES proyectos(pk_proyecto_id)
    )""")
    # Índices adicionales para columnas de consulta frecuente
    for _idx in [
        "CREATE INDEX IF NOT EXISTS idx_pqrs_fecha_limite    ON pqrs(fecha_limite)",
        "CREATE INDEX IF NOT EXISTS idx_pqrs_sui_export      ON pqrs(mes_reporte, reportado_sui)",
        "CREATE INDEX IF NOT EXISTS idx_audit_usuario         ON audit_log(usuario)",
        "CREATE INDEX IF NOT EXISTS idx_rc_area_estado        ON registro_central(area, estado)",
        "CREATE INDEX IF NOT EXISTS idx_tp_estado             ON tareas_proyecto(estado, proyecto_id)",
    ]:
        try: conn.execute(_idx)
        except Exception: pass

    conn.execute("""CREATE TABLE IF NOT EXISTS tipos_documento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        activo INTEGER DEFAULT 1,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS firmas_digitales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL, cargo TEXT NOT NULL,
        firma_base64 TEXT, activo INTEGER DEFAULT 1,
        es_aprobador_formato INTEGER DEFAULT 0,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS config_aprobador_formato (
        id INTEGER PRIMARY KEY DEFAULT 1,
        nombre TEXT NOT NULL DEFAULT 'Representante Legal',
        cargo TEXT NOT NULL DEFAULT 'Presidente',
        firma_id INTEGER, actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("INSERT OR IGNORE INTO config_aprobador_formato (id,nombre,cargo) VALUES (1,'José Humberto Ramírez','Representante Legal')")
    conn.commit()
    conn.close()
    print("  -> 31 tablas + indices + datos semilla listos.")
    print("  OK Inicializacion completada.")


def inicializar_tablas_arquitectura():
    """Tablas de la arquitectura objetivo: Convenios, Tesorería, Compras, Activos, IA"""
    conn = get_db()
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS convenios (
            pk_convenio_id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL, nombre TEXT NOT NULL,
            entidad_financiadora TEXT, objeto TEXT,
            valor_aprobado REAL DEFAULT 0,
            fecha_inicio TEXT, fecha_fin TEXT,
            estado TEXT DEFAULT 'activo',
            creado_por TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS contratos (
            pk_contrato_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_convenio_id INTEGER, numero TEXT, tipo TEXT,
            contratista TEXT, objeto TEXT, valor REAL DEFAULT 0,
            plazo_meses INTEGER, fecha_inicio TEXT, fecha_fin TEXT,
            estado TEXT DEFAULT 'activo', creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS adiciones (
            pk_adicion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_contrato_id INTEGER, monto_adicionado REAL DEFAULT 0,
            motivo TEXT, fecha_aprobacion TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS suspensiones (
            pk_suspension_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_contrato_id INTEGER, fecha_inicio TEXT, fecha_fin TEXT,
            causa TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS prorrogas (
            pk_prorroga_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_contrato_id INTEGER, nueva_fecha_fin TEXT,
            justificacion TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS cuentas_bancarias (
            pk_cuenta_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER, fk_convenio_id INTEGER,
            nombre_banco TEXT NOT NULL, numero_cuenta TEXT NOT NULL,
            titular TEXT, saldo_inicial REAL DEFAULT 0, saldo_actual REAL DEFAULT 0,
            estado TEXT DEFAULT 'activa', creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS caja_menor (
            pk_caja_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER, responsable TEXT,
            saldo_actual REAL DEFAULT 0, limite_maximo REAL DEFAULT 1000000,
            estado TEXT DEFAULT 'activa', creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS conciliaciones (
            pk_conciliacion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_cuenta_id INTEGER, fecha_corte TEXT,
            saldo_segun_banco REAL DEFAULT 0, saldo_segun_libros REAL DEFAULT 0,
            diferencia REAL DEFAULT 0, ajustes TEXT, creado_por TEXT,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS compras (
            pk_compra_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER, fk_convenio_id INTEGER,
            concepto TEXT NOT NULL, proveedor TEXT, valor REAL DEFAULT 0,
            fecha_requerimiento TEXT, fecha_orden_compra TEXT, fecha_recibido TEXT,
            numero_factura TEXT, estado TEXT DEFAULT 'solicitado',
            comprobante_path TEXT, creado_por TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS activos (
            pk_activo_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER, fk_compra_id INTEGER,
            codigo TEXT UNIQUE, tipo_activo TEXT, descripcion TEXT NOT NULL,
            serial TEXT, placa TEXT, valor REAL DEFAULT 0, fecha_ingreso TEXT,
            ubicacion_gps TEXT, vida_util_meses INTEGER, garantia_meses INTEGER,
            estado TEXT DEFAULT 'operativo', creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS mantenimientos (
            pk_mant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_activo_id INTEGER, fecha TEXT, tipo_mantenimiento TEXT DEFAULT 'preventivo',
            descripcion TEXT, costo REAL DEFAULT 0, responsable TEXT,
            proxima_fecha TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS actividades_proyecto (
            pk_actividad_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER NOT NULL, nombre_actividad TEXT NOT NULL,
            descripcion TEXT, responsable TEXT,
            fecha_inicio_plan TEXT, fecha_fin_plan TEXT,
            fecha_inicio_real TEXT, fecha_fin_real TEXT,
            costo_estimado REAL DEFAULT 0, costo_real REAL DEFAULT 0,
            porcentaje_avance INTEGER DEFAULT 0,
            estado TEXT DEFAULT 'pendiente', orden INTEGER DEFAULT 0,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS hitos (
            pk_hito_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER NOT NULL, descripcion TEXT NOT NULL,
            fecha_limite TEXT, cumplido INTEGER DEFAULT 0,
            fecha_cumplimiento TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS actividad_costos (
            fk_actividad_id INTEGER, fk_movimiento_id INTEGER,
            PRIMARY KEY (fk_actividad_id, fk_movimiento_id)
        );
        CREATE TABLE IF NOT EXISTS presupuesto_proyecto (
            pk_pres_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER NOT NULL, concepto TEXT NOT NULL,
            rubro TEXT, monto_asignado REAL DEFAULT 0,
            monto_ejecutado REAL DEFAULT 0, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS evidencias (
            pk_evidencia_id INTEGER PRIMARY KEY AUTOINCREMENT,
            entidad_tipo TEXT NOT NULL, entidad_id INTEGER NOT NULL,
            nombre_archivo TEXT NOT NULL, archivo_path TEXT NOT NULL,
            tipo_archivo TEXT, tamano_bytes INTEGER, hash_sha256 TEXT,
            descripcion TEXT, subido_por TEXT, fecha_subida TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS puntos_interes (
            pk_punto_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER, tipo TEXT, nombre TEXT,
            descripcion TEXT, como_llegar TEXT, lat REAL, lng REAL,
            fotos_paths TEXT, creado_por TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS trazas_redes (
            pk_traza_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER, tipo_tuberia TEXT, diametro_mm REAL,
            material TEXT, longitud_m REAL, geojson_linea TEXT,
            estado TEXT DEFAULT 'operativa', creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS prompts_ia (
            pk_prompt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL, categoria TEXT, template TEXT NOT NULL,
            descripcion TEXT, ultimo_uso TEXT, activo INTEGER DEFAULT 1,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS respuestas_ia_cache (
            pk_cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_hash TEXT UNIQUE, prompt_resumen TEXT, respuesta TEXT,
            modelo TEXT, tokens_usados INTEGER, fecha TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_convenios_estado    ON convenios(estado);
        CREATE INDEX IF NOT EXISTS idx_contratos_convenio  ON contratos(fk_convenio_id);
        CREATE INDEX IF NOT EXISTS idx_compras_proyecto    ON compras(fk_proyecto_id);
        CREATE INDEX IF NOT EXISTS idx_activos_proyecto    ON activos(fk_proyecto_id);
        CREATE INDEX IF NOT EXISTS idx_actividades_proy    ON actividades_proyecto(fk_proyecto_id);
        CREATE INDEX IF NOT EXISTS idx_evidencias_entidad  ON evidencias(entidad_tipo, entidad_id);
        """)
        conn.commit()
        print("  -> Tablas arquitectura objetivo creadas.")
    except Exception as e:
        print(f"  ⚠ Error en tablas arquitectura: {e}")
    finally:
        conn.close()




def inicializar_bancos_default():
    """Crea cuentas bancarias base si la tabla esta vacia."""
    conn = get_db()
    try:
        n = conn.execute("SELECT COUNT(*) FROM bancos").fetchone()[0]
        if n == 0:
            conn.execute(
                "INSERT INTO bancos (codigo_cuenta,banco_nombre,tipo_cuenta,moneda,"
                "saldo_actual,ejecutivo,telefono,status) VALUES (?,?,?,?,?,?,?,?)",
                ('CAJ-001','Caja General','EFECTIVO','COP',0,'Tesorero','','ACTIVA'))
            conn.execute(
                "INSERT INTO bancos (codigo_cuenta,banco_nombre,tipo_cuenta,moneda,"
                "saldo_actual,ejecutivo,telefono,status) VALUES (?,?,?,?,?,?,?,?)",
                ('BCO-001','Banco Principal','AHORRO','COP',0,'Tesorero','','ACTIVA'))
            conn.commit()
            print("  -> Bancos iniciales creados.")
    except Exception as e:
        print(f"  ⚠ Bancos default: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inicializar_base_datos()


# ═══════════════════════════════════════════════════════════════════
# TABLAS EXTRA - PROGRAMA_1.doc + PROGRAMA_2.doc
# Llamar esta funcion DESPUES de inicializar_base_datos()
# ═══════════════════════════════════════════════════════════════════
def inicializar_tablas_extra(conn=None):
    """Crea tablas extra del PROGRAMA_1 y PROGRAMA_2 sin duplicar."""
    import sqlite3 as _sq
    c2 = conn or _sq.connect(DB)
    c2.execute("PRAGMA foreign_keys=ON")

    # ── Firmantes por documento (tabla faltante) ─────────────────────
    c2.execute("""CREATE TABLE IF NOT EXISTS documento_firmantes (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        documento_id     INTEGER NOT NULL,
        firmante_id      INTEGER NOT NULL,
        orden_firma      INTEGER DEFAULT 1,
        estado           TEXT DEFAULT 'pendiente'
                         CHECK(estado IN('pendiente','aprobado','rechazado','omitido')),
        fecha_aprobacion TEXT,
        observacion      TEXT,
        UNIQUE(documento_id, firmante_id),
        FOREIGN KEY(documento_id) REFERENCES registro_central(pk_registro_id) ON DELETE CASCADE,
        FOREIGN KEY(firmante_id) REFERENCES firmantes(pk_firmante_id)
    )""")

    # ── PROGRAMA_2.doc: Juego de reciclaje comunitario ──────────────
    c2.execute("""CREATE TABLE IF NOT EXISTS juego_config (
        id INTEGER PRIMARY KEY DEFAULT 1,
        juego_activo INTEGER DEFAULT 1,
        premio_descripcion TEXT,
        fecha_entrega TEXT,
        puntos_reciclaje INTEGER DEFAULT 10,
        puntos_reutilizacion INTEGER DEFAULT 15,
        puntos_reforestacion INTEGER DEFAULT 20,
        puntos_mejoramiento INTEGER DEFAULT 12,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c2.execute("INSERT OR IGNORE INTO juego_config (id) VALUES (1)")

    c2.execute("""CREATE TABLE IF NOT EXISTS juego_fotos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fk_usuario_id INTEGER NOT NULL,
        foto_path TEXT NOT NULL,
        categoria TEXT CHECK(categoria IN('reciclaje','reutilizacion','reforestacion','mejoramiento')),
        descripcion TEXT,
        puntos INTEGER DEFAULT 0,
        estado TEXT DEFAULT 'pendiente' CHECK(estado IN('pendiente','aprobada','rechazada')),
        razon_rechazo TEXT,
        subida_en TEXT DEFAULT CURRENT_TIMESTAMP,
        revisada_en TEXT,
        aprobado_por INTEGER,
        FOREIGN KEY(fk_usuario_id) REFERENCES usuarios(pk_usuario_id)
    )""")

    c2.execute("""CREATE TABLE IF NOT EXISTS juego_puntos (
        fk_usuario_id INTEGER PRIMARY KEY,
        total_puntos INTEGER DEFAULT 0,
        fotos_aprobadas INTEGER DEFAULT 0,
        ultima_actividad TEXT,
        FOREIGN KEY(fk_usuario_id) REFERENCES usuarios(pk_usuario_id)
    )""")

    # ── PROGRAMA_2.doc: Reportes semanales con aprobacion ──────────
    c2.execute("""CREATE TABLE IF NOT EXISTS reportes_semanales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        consecutivo INTEGER NOT NULL DEFAULT 1,
        semana_inicio TEXT NOT NULL,
        semana_fin TEXT NOT NULL,
        datos_json TEXT NOT NULL,
        observaciones TEXT,
        estado TEXT DEFAULT 'borrador'
                 CHECK(estado IN('borrador','en_aprobacion','aprobado','rechazado')),
        pdf_path TEXT,
        creado_por INTEGER NOT NULL,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        aprobado_por INTEGER,
        aprobado_en TEXT,
        rechazado_por INTEGER,
        rechazado_en TEXT,
        FOREIGN KEY(creado_por) REFERENCES usuarios(pk_usuario_id),
        FOREIGN KEY(aprobado_por) REFERENCES usuarios(pk_usuario_id)
    )""")

    # ── PROGRAMA_2.doc: Bloqueo de usuarios por intentos fallidos ──
    try:
        c2.execute("ALTER TABLE usuarios ADD COLUMN bloqueado INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        c2.execute("ALTER TABLE usuarios ADD COLUMN intentos_fallidos INTEGER DEFAULT 0")
    except Exception:
        pass

    # ── PROGRAMA_1.doc: Infraestructura PUEAA extendida ────────────
    c2.execute("""CREATE TABLE IF NOT EXISTS infraestructura_pueaa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT CHECK(tipo IN('Bocatoma','Aduccion','Desarenador','PTAP','Conduccion',
                                'Almacenamiento','Distribucion')),
        nombre TEXT NOT NULL,
        estado TEXT DEFAULT 'Operativo',
        longitud_m REAL,
        diametro_pulg REAL,
        material TEXT,
        anio_instalacion INTEGER,
        observaciones TEXT,
        zona_id INTEGER,
        lat REAL, lon REAL,
        FOREIGN KEY(zona_id) REFERENCES zonas_prestacion(pk_zona_id)
    )""")

    c2.execute("""CREATE TABLE IF NOT EXISTS aforos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        punto TEXT NOT NULL,
        tipo_punto TEXT CHECK(tipo_punto IN('Bocatoma','Salida_PTAP','Entrada_Tanque',
                                            'Salida_Tanque','Punto_Red')),
        fecha TEXT NOT NULL,
        caudal_ls REAL NOT NULL,
        responsable TEXT,
        observaciones TEXT,
        fk_infra_id INTEGER,
        FOREIGN KEY(fk_infra_id) REFERENCES infraestructura_pueaa(id)
    )""")

    c2.execute("""CREATE TABLE IF NOT EXISTS actividades_pueaa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proyecto_pueaa INTEGER CHECK(proyecto_pueaa BETWEEN 8 AND 14),
        nombre_actividad TEXT NOT NULL,
        descripcion TEXT,
        costo_estimado REAL DEFAULT 0,
        costo_real REAL,
        fecha_inicio TEXT,
        fecha_fin TEXT,
        avance_pct REAL DEFAULT 0,
        meta_quinquenal TEXT,
        evidencia_path TEXT,
        responsable TEXT,
        anio INTEGER
    )""")

    # ── PROGRAMA_1.doc: Calidad del agua IRCA ──────────────────────
    c2.execute("""CREATE TABLE IF NOT EXISTS registros_irca (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        punto_muestreo TEXT,
        turbidez REAL,
        ph REAL,
        cloro_residual REAL,
        coliformes_totales TEXT,
        irca_calculado REAL,
        nivel_riesgo TEXT CHECK(nivel_riesgo IN('Sin riesgo','Bajo','Medio','Alto','Inviable')),
        observaciones TEXT,
        responsable TEXT
    )""")

    # ── PROGRAMA_1.doc: Nuevos parametros de configuracion ─────────
    cfgs_extra = [
        ("longitud_red_km",       "12.5",  "Longitud total red de distribucion (km)", "Tecnica", "numero", None, 20),
        ("horas_servicio_dia",    "18",    "Horas de servicio diario promedio",        "Tecnica", "numero", None, 21),
        ("empleados_operativos",  "3",     "Numero de empleados operativos",           "Tecnica", "numero", None, 22),
        ("total_viviendas",       "260",   "Total viviendas zona de prestacion",       "Tecnica", "numero", None, 23),
        ("kwh_anuales",           "0",     "Consumo energetico anual (kWh)",           "Tecnica", "numero", None, 24),
        ("macromedidores_func",   "1",     "Macromedidores en funcionamiento",         "Tecnica", "numero", None, 25),
        ("total_tramos",          "3",     "Total tramos de red (para IMA)",           "Tecnica", "numero", None, 26),
        ("irca_ultimo",           "5",     "IRCA ultimo reporte (%)",                  "Tecnica", "numero", "balance", 27),
        ("caudal_concesionado_ls","3.5",   "Caudal concesionado en la Quebrada (l/s)", "Tecnica", "numero", None, 28),
        ("correo_car",            "sau@car.gov.co", "Correo oficial CAR para envio PUEAA", "Notificaciones","texto",None,10),
        ("eslogan",               "Gestion comunitaria para el agua y el desarrollo sostenible",
                                          "Eslogan institucional para PDFs",          "Institucional","texto",None,11),
    ]
    c2.executemany("""
        INSERT OR IGNORE INTO configuracion(clave,valor,descripcion,categoria,tipo_dato,modulo,orden)
        VALUES(?,?,?,?,?,?,?)
    """, cfgs_extra)

    if not conn:
        c2.commit(); c2.close()
    else:
        c2.commit()
    print("  -> Tablas extra (PROGRAMA_1+2) creadas.")



def inicializar_tablas_arquitectura():
    """Tablas de la arquitectura objetivo: Convenios, Tesorería, Compras, Activos, IA"""
    conn = get_db()
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS convenios (
            pk_convenio_id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL, nombre TEXT NOT NULL,
            entidad_financiadora TEXT, objeto TEXT,
            valor_aprobado REAL DEFAULT 0,
            fecha_inicio TEXT, fecha_fin TEXT,
            estado TEXT DEFAULT 'activo',
            creado_por TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS contratos (
            pk_contrato_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_convenio_id INTEGER, numero TEXT, tipo TEXT,
            contratista TEXT, objeto TEXT, valor REAL DEFAULT 0,
            plazo_meses INTEGER, fecha_inicio TEXT, fecha_fin TEXT,
            estado TEXT DEFAULT 'activo', creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS adiciones (
            pk_adicion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_contrato_id INTEGER, monto_adicionado REAL DEFAULT 0,
            motivo TEXT, fecha_aprobacion TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS suspensiones (
            pk_suspension_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_contrato_id INTEGER, fecha_inicio TEXT, fecha_fin TEXT,
            causa TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS prorrogas (
            pk_prorroga_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_contrato_id INTEGER, nueva_fecha_fin TEXT,
            justificacion TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS cuentas_bancarias (
            pk_cuenta_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER, fk_convenio_id INTEGER,
            nombre_banco TEXT NOT NULL, numero_cuenta TEXT NOT NULL,
            titular TEXT, saldo_inicial REAL DEFAULT 0, saldo_actual REAL DEFAULT 0,
            estado TEXT DEFAULT 'activa', creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS caja_menor (
            pk_caja_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER, responsable TEXT,
            saldo_actual REAL DEFAULT 0, limite_maximo REAL DEFAULT 1000000,
            estado TEXT DEFAULT 'activa', creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS conciliaciones (
            pk_conciliacion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_cuenta_id INTEGER, fecha_corte TEXT,
            saldo_segun_banco REAL DEFAULT 0, saldo_segun_libros REAL DEFAULT 0,
            diferencia REAL DEFAULT 0, ajustes TEXT, creado_por TEXT,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS compras (
            pk_compra_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER, fk_convenio_id INTEGER,
            concepto TEXT NOT NULL, proveedor TEXT, valor REAL DEFAULT 0,
            fecha_requerimiento TEXT, fecha_orden_compra TEXT, fecha_recibido TEXT,
            numero_factura TEXT, estado TEXT DEFAULT 'solicitado',
            comprobante_path TEXT, creado_por TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS activos (
            pk_activo_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER, fk_compra_id INTEGER,
            codigo TEXT UNIQUE, tipo_activo TEXT, descripcion TEXT NOT NULL,
            serial TEXT, placa TEXT, valor REAL DEFAULT 0, fecha_ingreso TEXT,
            ubicacion_gps TEXT, vida_util_meses INTEGER, garantia_meses INTEGER,
            estado TEXT DEFAULT 'operativo', creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS mantenimientos (
            pk_mant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_activo_id INTEGER, fecha TEXT, tipo_mantenimiento TEXT DEFAULT 'preventivo',
            descripcion TEXT, costo REAL DEFAULT 0, responsable TEXT,
            proxima_fecha TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS actividades_proyecto (
            pk_actividad_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER NOT NULL, nombre_actividad TEXT NOT NULL,
            descripcion TEXT, responsable TEXT,
            fecha_inicio_plan TEXT, fecha_fin_plan TEXT,
            fecha_inicio_real TEXT, fecha_fin_real TEXT,
            costo_estimado REAL DEFAULT 0, costo_real REAL DEFAULT 0,
            porcentaje_avance INTEGER DEFAULT 0,
            estado TEXT DEFAULT 'pendiente', orden INTEGER DEFAULT 0,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS hitos (
            pk_hito_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER NOT NULL, descripcion TEXT NOT NULL,
            fecha_limite TEXT, cumplido INTEGER DEFAULT 0,
            fecha_cumplimiento TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS actividad_costos (
            fk_actividad_id INTEGER, fk_movimiento_id INTEGER,
            PRIMARY KEY (fk_actividad_id, fk_movimiento_id)
        );
        CREATE TABLE IF NOT EXISTS presupuesto_proyecto (
            pk_pres_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER NOT NULL, concepto TEXT NOT NULL,
            rubro TEXT, monto_asignado REAL DEFAULT 0,
            monto_ejecutado REAL DEFAULT 0, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS evidencias (
            pk_evidencia_id INTEGER PRIMARY KEY AUTOINCREMENT,
            entidad_tipo TEXT NOT NULL, entidad_id INTEGER NOT NULL,
            nombre_archivo TEXT NOT NULL, archivo_path TEXT NOT NULL,
            tipo_archivo TEXT, tamano_bytes INTEGER, hash_sha256 TEXT,
            descripcion TEXT, subido_por TEXT, fecha_subida TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS puntos_interes (
            pk_punto_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER, tipo TEXT, nombre TEXT,
            descripcion TEXT, como_llegar TEXT, lat REAL, lng REAL,
            fotos_paths TEXT, creado_por TEXT, creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS trazas_redes (
            pk_traza_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_proyecto_id INTEGER, tipo_tuberia TEXT, diametro_mm REAL,
            material TEXT, longitud_m REAL, geojson_linea TEXT,
            estado TEXT DEFAULT 'operativa', creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS prompts_ia (
            pk_prompt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL, categoria TEXT, template TEXT NOT NULL,
            descripcion TEXT, ultimo_uso TEXT, activo INTEGER DEFAULT 1,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS respuestas_ia_cache (
            pk_cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_hash TEXT UNIQUE, prompt_resumen TEXT, respuesta TEXT,
            modelo TEXT, tokens_usados INTEGER, fecha TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_convenios_estado    ON convenios(estado);
        CREATE INDEX IF NOT EXISTS idx_contratos_convenio  ON contratos(fk_convenio_id);
        CREATE INDEX IF NOT EXISTS idx_compras_proyecto    ON compras(fk_proyecto_id);
        CREATE INDEX IF NOT EXISTS idx_activos_proyecto    ON activos(fk_proyecto_id);
        CREATE INDEX IF NOT EXISTS idx_actividades_proy    ON actividades_proyecto(fk_proyecto_id);
        CREATE INDEX IF NOT EXISTS idx_evidencias_entidad  ON evidencias(entidad_tipo, entidad_id);
        """)
        conn.commit()
        print("  -> Tablas arquitectura objetivo creadas.")
    except Exception as e:
        print(f"  ⚠ Error en tablas arquitectura: {e}")
    finally:
        conn.close()




def inicializar_bancos_default():
    """Crea cuentas bancarias base si la tabla esta vacia."""
    conn = get_db()
    try:
        n = conn.execute("SELECT COUNT(*) FROM bancos").fetchone()[0]
        if n == 0:
            conn.execute(
                "INSERT INTO bancos (codigo_cuenta,banco_nombre,tipo_cuenta,moneda,"
                "saldo_actual,ejecutivo,telefono,status) VALUES (?,?,?,?,?,?,?,?)",
                ('CAJ-001','Caja General','EFECTIVO','COP',0,'Tesorero','','ACTIVA'))
            conn.execute(
                "INSERT INTO bancos (codigo_cuenta,banco_nombre,tipo_cuenta,moneda,"
                "saldo_actual,ejecutivo,telefono,status) VALUES (?,?,?,?,?,?,?,?)",
                ('BCO-001','Banco Principal','AHORRO','COP',0,'Tesorero','','ACTIVA'))
            conn.commit()
            print("  -> Bancos iniciales creados.")
    except Exception as e:
        print(f"  ⚠ Bancos default: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inicializar_base_datos()
    conn_main = __import__('sqlite3').connect(DB)
    conn_main.execute("PRAGMA foreign_keys=ON")
    inicializar_tablas_extra(conn_main)
    conn_main.close()
    print("=" * 60)
    print("  INICIALIZACION COMPLETA v2 (PROGRAMA_1 + PROGRAMA_2)")
    print("=" * 60)


def inicializar_tablas_prog3_prog4(conn=None):
    """
    Tablas de PROGRAMA_3 (auditoría, usuarios con foto)
    y PROGRAMA_4 (proyectos extendidos con Gantt, dependencias, costos, ingresos, riesgos, metas).
    """
    import sqlite3 as _sq
    c2 = conn or _sq.connect(DB)
    c2.execute("PRAGMA foreign_keys=ON")

    # Agregar columnas faltantes a proyectos existente (si vienen de version anterior)
    for col_def in [
        ("objetivo",         "TEXT"),
        ("tipo_proyecto",    "TEXT DEFAULT 'otro'"),
        ("ingresos_totales", "REAL DEFAULT 0"),
        ("creado_por",       "INTEGER"),
        ("actualizado_en",   "TEXT"),
    ]:
        try:
            c2.execute(f"ALTER TABLE proyectos ADD COLUMN {col_def[0]} {col_def[1]}")
        except Exception:
            pass  # ya existe

    # Agregar tablas dependencias, costos_reales, ingresos, metas_proyecto
    # si no existen (pueden haber sido creadas previamente con otro schema)

    # ── PROGRAMA_3: Auditoría ───────────────────────────────────────
    c2.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        nombre_usuario TEXT,
        accion TEXT NOT NULL,
        modulo TEXT NOT NULL,
        descripcion TEXT,
        ip_address TEXT,
        user_agent TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c2.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(usuario_id)")
    c2.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(timestamp)")
    c2.execute("CREATE INDEX IF NOT EXISTS idx_audit_mod ON audit_log(modulo)")

    # ── PROGRAMA_3: Autorizaciones OTP extendidas ───────────────────
    c2.execute("""CREATE TABLE IF NOT EXISTS autorizaciones_extendidas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        documento_id INTEGER NOT NULL,
        firmante_id INTEGER NOT NULL,
        tipo TEXT NOT NULL CHECK(tipo IN('OTP','APROBACION_MANUAL','RECHAZO')),
        codigo_otp TEXT,
        resultado TEXT NOT NULL CHECK(resultado IN('exito','fallido','expirado','rechazado')),
        ip_address TEXT,
        user_agent TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c2.execute("CREATE INDEX IF NOT EXISTS idx_autx_doc ON autorizaciones_extendidas(documento_id)")

    # ── PROGRAMA_3: Foto de usuario ─────────────────────────────────
    try:
        c2.execute("ALTER TABLE usuarios ADD COLUMN foto_path TEXT")
    except Exception:
        pass

    # ── PROGRAMA_4: Proyectos extendidos ────────────────────────────
    c2.execute("""CREATE TABLE IF NOT EXISTS proyectos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        objetivo TEXT,
        tipo_proyecto TEXT NOT NULL DEFAULT 'otro',
        estado TEXT DEFAULT 'planificacion',
        fecha_inicio_plan TEXT,
        fecha_fin_plan TEXT,
        fecha_inicio_real TEXT,
        fecha_fin_real TEXT,
        presupuesto_total REAL DEFAULT 0,
        costo_real REAL DEFAULT 0,
        ingresos_totales REAL DEFAULT 0,
        porcentaje_avance INTEGER DEFAULT 0,
        responsable_id INTEGER,
        creado_por INTEGER,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT
    )""")
    c2.execute("CREATE INDEX IF NOT EXISTS idx_proy_estado ON proyectos(estado)")
    c2.execute("CREATE INDEX IF NOT EXISTS idx_proy_tipo ON proyectos(tipo_proyecto)")

    c2.execute("""CREATE TABLE IF NOT EXISTS tareas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proyecto_id INTEGER NOT NULL,
        padre_id INTEGER,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        prioridad TEXT DEFAULT 'media',
        estado TEXT DEFAULT 'pendiente',
        fecha_inicio_plan TEXT,
        fecha_fin_plan TEXT,
        fecha_inicio_real TEXT,
        fecha_fin_real TEXT,
        duracion_estimada_dias INTEGER,
        porcentaje_avance INTEGER DEFAULT 0,
        responsable_id INTEGER,
        costo_estimado REAL DEFAULT 0,
        costo_real REAL DEFAULT 0,
        orden INTEGER DEFAULT 0,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(proyecto_id) REFERENCES proyectos(pk_proyecto_id) ON DELETE CASCADE
    )""")
    try:
        c2.execute("CREATE INDEX IF NOT EXISTS idx_tar_proy ON tareas(proyecto_id)")
    except Exception: pass
    try:
        c2.execute("CREATE INDEX IF NOT EXISTS idx_tar_est ON tareas(estado)")
    except Exception: pass

    c2.execute("""CREATE TABLE IF NOT EXISTS dependencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarea_id INTEGER NOT NULL,
        tarea_dependiente_id INTEGER NOT NULL,
        tipo TEXT DEFAULT 'FS',
        FOREIGN KEY(tarea_id) REFERENCES tareas(id) ON DELETE CASCADE,
        FOREIGN KEY(tarea_dependiente_id) REFERENCES tareas(id) ON DELETE CASCADE
    )""")

    c2.execute("""CREATE TABLE IF NOT EXISTS costos_reales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proyecto_id INTEGER NOT NULL,
        tarea_id INTEGER,
        fecha TEXT NOT NULL,
        concepto TEXT NOT NULL,
        monto REAL NOT NULL,
        comprobante TEXT,
        registrado_por INTEGER,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(proyecto_id) REFERENCES proyectos(pk_proyecto_id) ON DELETE CASCADE
    )""")
    try:
        c2.execute("CREATE INDEX IF NOT EXISTS idx_cost_proy ON costos_reales(proyecto_id)")
    except Exception: pass

    c2.execute("""CREATE TABLE IF NOT EXISTS ingresos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proyecto_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        fuente TEXT NOT NULL,
        concepto TEXT,
        monto REAL NOT NULL,
        comprobante TEXT,
        registrado_por INTEGER,
        FOREIGN KEY(proyecto_id) REFERENCES proyectos(pk_proyecto_id) ON DELETE CASCADE
    )""")
    try:
        c2.execute("CREATE INDEX IF NOT EXISTS idx_ingr_proy ON ingresos(proyecto_id)")
    except Exception: pass

    c2.execute("""CREATE TABLE IF NOT EXISTS riesgos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proyecto_id INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        probabilidad TEXT,
        impacto TEXT,
        plan_mitigacion TEXT,
        responsable_id INTEGER,
        estado TEXT DEFAULT 'identificado',
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(proyecto_id) REFERENCES proyectos(pk_proyecto_id) ON DELETE CASCADE
    )""")

    c2.execute("""CREATE TABLE IF NOT EXISTS metas_proyecto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proyecto_id INTEGER NOT NULL,
        anio INTEGER NOT NULL,
        semestre INTEGER,
        meta TEXT NOT NULL,
        cumplida INTEGER DEFAULT 0,
        observaciones TEXT,
        FOREIGN KEY(proyecto_id) REFERENCES proyectos(pk_proyecto_id) ON DELETE CASCADE
    )""")

    if not conn:
        c2.commit(); c2.close()
    else:
        c2.commit()
    print("  -> Tablas PROGRAMA_3 + PROGRAMA_4 creadas.")

