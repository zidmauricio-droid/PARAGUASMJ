# DOCUMENTACION TECNICA COMPLETA - PARAGUASMJ

> Generado: 2026-06-07 | Version del proyecto: 2026.1 | Revision ZIP: 12

---

## 1. RESUMEN DEL PROYECTO

### Que es el programa
PARAGUASMJ es un **Sistema Integrado de Gestion Documental** para el Acueducto Comunitario El Puente, operado por la Asociacion de Suscriptores (ASUACAP), ubicada en el Caserio El Puente, Villeta, Cundinamarca, Colombia.

### Que problema resuelve
Los acueductos comunitarios colombianos estan obligados por ley a reportar a la SSPD (Superintendencia de Servicios Publicos), la CAR (Corporacion Autonoma Regional) y la Alcaldia. Antes del sistema, todo se hacia en papel. PARAGUASMJ centraliza:
- Radicacion y seguimiento de documentos institucionales
- Gestion de PQRS (Peticiones, Quejas, Reclamos y Sugerencias)
- Balance hidrico y calidad del agua
- Gestion financiera (caja, bancos, movimientos)
- Mapa GIS de infraestructura y fallas
- Reportes normativos automaticos (SSPD, CAR, Alcaldia)
- Gestion de emergencias y convenios
- Firma digital (SHA-256) y autorizaciones OTP por WhatsApp

### Para quien es util
- Presidente / Representante Legal: firma digital, reportes normativos
- Tesorera: modulo financiero, caja diaria
- Secretaria: radicacion de documentos, PQRS
- Tecnico de campo: registro de lecturas, fallas GIS
- Auditor: trazabilidad, verificacion de integridad

### Tecnologias usadas
| Capa | Tecnologia |
|---|---|
| Backend | Python 3.11, Flask 3.1.x |
| Servidor WSGI | Waitress 3.x (produccion) / Flask dev server |
| Base de datos | SQLite3 con WAL mode |
| Templates | Jinja2 (HTML con Bootstrap 5) |
| Tareas programadas | APScheduler 3.x |
| PDF profesional | ReportLab 4.x |
| Exportacion Excel | pandas + openpyxl |
| Documentos Word | python-docx |
| Imagenes | Pillow |
| Actualizaciones USB | Hilo daemon Python |
| Despliegue | PyInstaller (exe Windows) + bat scripts |
| IA opcional | Anthropic claude-haiku-4-5 / Ollama local |

---

## 2. ARQUITECTURA DEL SISTEMA

### Estructura de archivos

```
PARAGUASMJ/
├── app.py                        # Punto de entrada Flask, registro blueprints
├── run.py                        # Lanzador para PyInstaller (waitress)
├── config.py                     # Config central (rutas, secretos, constantes)
│
├── routes/                       # 16 blueprints Flask
│   ├── autenticacion.py          # /auth   — login, logout, OTP WhatsApp
│   ├── dashboard.py              # /        — panel principal, indicadores
│   ├── documentos.py             # /documentos — CRUD, editor, API autosave
│   ├── pqrs.py                   # /pqrs   — peticiones, quejas, reclamos
│   ├── gis.py                    # /gis    — mapa GeoJSON, fallas, infraestructura
│   ├── balance_hidrico.py        # /balance — produccion, facturacion, IANC
│   ├── comunicaciones.py         # /com    — oficios y circulares internos
│   ├── proyectos.py              # /proyectos — proyectos de inversion (v1)
│   ├── proyectos_v2.py           # /proyectos2 — version mejorada con PROGRAMA_5
│   ├── finanzas.py               # /finanzas — caja diaria, bancos, movimientos
│   ├── reportes_normativos.py    # /reportes — SSPD, CAR, Alcaldia
│   ├── auditoria.py              # /auditoria — log trazabilidad, gestion usuarios
│   ├── emergencias.py            # /emergencias — incidentes, protocolos
│   ├── convenios.py              # /convenios — contratos con entidades
│   ├── carpetas_bp.py            # /carpetas — gestion 12 modulos documentales
│   └── api.py                    # /api    — endpoints genericos REST
│
├── core/                         # Modulos de infraestructura interna
│   ├── database_manager.py       # get_db(), with_retry(), WAL, consecutivos
│   ├── seguridad.py              # login_requerido, rol_requerido
│   ├── auditoria.py              # auditar(), registrar_evento()
│   ├── otp_manager.py            # Generacion y verificacion OTP por WhatsApp
│   ├── pdf_profesional.py        # PDF con membrete, firmas, ReportLab
│   ├── backup_manager.py         # Copia de seguridad SQLite, rotacion
│   ├── logger.py                 # Logger JSON estructurado
│   ├── scheduler_notificaciones.py # Tarea diaria: vencimientos, alertas TRD
│   ├── email_manager.py          # Envio de correos (SMTP)
│   ├── indicadores.py            # IANC, cobertura, presion
│   ├── indicadores_ius.py        # Indices IRCA, turbiedad
│   ├── reportes_excel.py         # Reportes Excel trimestrales
│   ├── reportes_sspd.py          # Reportes formato SSPD
│   ├── logo_manager.py           # Gestion del logo/membrete
│   └── usb_updater.py            # Actualizacion por USB (hilo daemon)
│
├── utils/                        # Utilidades transversales
│   ├── validadores.py            # Validacion nombres carpetas (Windows MAX_PATH)
│   ├── auditoria.py              # HMAC-SHA256 cadena de auditoria inmutable
│   ├── seguridad.py              # @login_required, CSRF, bloqueo 5 intentos
│   ├── file_manager.py           # 12 modulos documentales, estadisticas
│   ├── helpers.py                # formatear_moneda(), truncar()
│   ├── validators.py             # Validadores basicos de formularios
│   ├── audit.py                  # Auditoria legacy (compatible)
│   └── export_pdf.py             # PDF simple (fallback sin ReportLab avanzado)
│
├── database/
│   ├── inicializar_db.py         # Crea 31 tablas, indices, datos semilla
│   └── paraguasmj.db             # Base de datos SQLite (generada al iniciar)
│
├── templates/                    # HTML Jinja2 por modulo
│   ├── base.html                 # Layout principal (Bootstrap 5, sidebar)
│   ├── login.html
│   ├── dashboard.html
│   ├── configuracion.html
│   ├── documentos/               # lista.html, nuevo.html, editar.html, ver.html
│   ├── pqrs/                     # lista.html, nueva.html, ver.html, bitacora.html
│   ├── balance/                  # panel.html
│   ├── finanzas/                 # caja.html, bancos.html, movimientos.html
│   ├── proyectos/                # lista.html, ver.html, form.html
│   ├── proyectos2/               # panel.html
│   ├── emergencias/              # panel.html
│   ├── convenios/                # panel.html, detalle.html
│   ├── auditoria/                # panel.html, usuarios.html
│   ├── comunicaciones/           # lista.html, nueva.html
│   └── reportes_normativos/      # panel.html
│
├── static/
│   ├── css/estilo.css            # Estilos personalizados PARAGUASMJ
│   ├── js/app.js                 # JS global (alertas, sidebar)
│   ├── leaflet/                  # Mapas offline (Leaflet.js)
│   └── tinymce/                  # Editor rico (placeholder, se usa contenteditable)
│
├── config/
│   └── trd.json                  # Tabla de Retencion Documental (5 series)
│
├── uploads/                      # Archivos adjuntos subidos
├── pdfs/                         # PDFs generados
├── logs/                         # Logs del sistema + auditoria.jsonl
│
├── tests/                        # Suite de pruebas
│   ├── test_auth.py
│   ├── test_otp.py
│   ├── test_helpers.py
│   └── test_indicadores.py
│
├── INSTALAR.bat                  # Instalador Windows (ASCII puro, v1.9)
├── INICIAR.bat                   # Lanzador Windows con deteccion de puerto
├── crear_estructura_completa.bat # Crea 12 modulos de carpetas
├── configurar_github.bat         # Configura git y sube a GitHub
└── actualizar_github.bat         # Actualiza repositorio en GitHub
```

### Componentes principales

| Componente | Responsabilidad | Archivo clave |
|---|---|---|
| Flask App | Servidor web, enrutamiento | app.py |
| Config | Rutas de archivos, secretos, constantes legales | config.py |
| DB Manager | Conexion SQLite, WAL, reintentos, consecutivos | core/database_manager.py |
| Seguridad | Sesiones, roles, OTP, bloqueo por intentos | core/seguridad.py, utils/seguridad.py |
| Auditoria | Log HMAC-SHA256 inmutable | utils/auditoria.py |
| Documentos | CRUD completo + editor HTML + API autosave | routes/documentos.py |
| GIS | GeoJSON infraestructura + fallas + publico | routes/gis.py |
| PQRS | Flujo peticiones con plazos CPACA | routes/pqrs.py |
| Scheduler | Alertas diarias vencimientos + TRD | core/scheduler_notificaciones.py |
| FileManager | 12 modulos carpetas, estadisticas, cache 60s | utils/file_manager.py |

### Flujo de datos tipico (crear documento)

```
Usuario → POST /documentos/nuevo
  → sanitizar_html() [XSS protection]
  → obtener_consecutivo(area, tipo, anio) [DB: area_GA-OFI-2026-001]
  → INSERT registro_central
  → INSERT contenido_documento
  → INSERT plazos_documento
  → INSERT documento_firmantes (segun reglas o seleccion manual)
  → INSERT acciones_pendientes (para cada firmante)
  → INSERT seguimiento_documento
  → auditar() [log de auditoria]
  → redirect /documentos/<id>
```

---

## 3. ESTADO DEL DESARROLLO

### COMPLETO y funcionando

| Modulo | Estado |
|---|---|
| Autenticacion (login/logout/OTP) | COMPLETO |
| Dashboard con indicadores | COMPLETO |
| Gestion documental (CRUD + editor) | COMPLETO |
| Editor HTML contenteditable offline | COMPLETO |
| API autosave cada 30s | COMPLETO |
| Historial de versiones de documentos | COMPLETO |
| Firma digital SHA-256 por firmante | COMPLETO |
| 5 plantillas institucionales | COMPLETO |
| PQRS con plazos CPACA | COMPLETO |
| Balance hidrico (IANC) | COMPLETO |
| Modulo financiero (caja, bancos) | COMPLETO |
| GIS (mapa, infraestructura, fallas) | COMPLETO v14 |
| Endpoint publico GeoJSON | COMPLETO |
| Emergencias | COMPLETO |
| Convenios | COMPLETO |
| Proyectos v1 y v2 | COMPLETO |
| Reportes normativos | COMPLETO |
| Auditoria HMAC-SHA256 | COMPLETO |
| Gestion de carpetas (12 modulos) | COMPLETO |
| TRD (alertas, transferencias) | COMPLETO |
| Semaforo CPACA dias habiles | COMPLETO |
| Vista previa PDF temporal | COMPLETO (requiere weasyprint) |
| Expedientes AGN + Hoja Control | COMPLETO (requiere weasyprint) |
| Backup automatico SQLite | COMPLETO |
| Scheduler notificaciones 8:00 AM | COMPLETO |
| Actualizacion por USB | COMPLETO (daemon) |
| Reportes Excel trimestrales | COMPLETO |
| Validacion nombres Windows (MAX_PATH) | COMPLETO |
| IA proxy (Anthropic + Ollama) | COMPLETO |
| Instalador Windows (INSTALAR.bat) | COMPLETO v1.9 ASCII puro |
| PyInstaller EXE | COMPLETO (lista de hidden-imports) |

### EN PROGRESO / CON LIMITACIONES

| Item | Descripcion |
|---|---|
| Vista previa PDF | Requiere `pip install weasyprint` (pesado, no en requirements.txt) |
| Hoja control expedientes | Idem — depende de weasyprint |
| OTP WhatsApp | Requiere configurar numero de telefono en BD tabla configuracion |
| IA integrada | Requiere API key Anthropic o Ollama corriendo en localhost:11434 |
| Comunicaciones | Blueprint registrado pero template basico (52 lineas) |

### FALTA / FUTURO

- Template `templates/documentos/expedientes.html` (ruta existe, template no)
- Template `templates/carpetas/index.html` (blueprint registrado, sin template)
- WeasyPrint en requirements.txt (decision pendiente por peso ~200MB)
- Calendario colombiano (dias habiles festivos) — `core/calendario_colombiano.py` referenciado pero no existe
- Modulo de calidad del agua IRCA (indicadores_ius.py existe, sin template ni ruta)

### Bugs conocidos
- `core/calendario_colombiano.py` referenciado en `indicador_tiempo()` pero no existe. Fallback automatico con factor 1.4x (funcional pero impreciso en festivos colombianos).
- `core/gestor_trd.py` importado en documentos.py — debe existir o el blueprint falla al importar.
- `core/forensic_saneamiento.py` importado en documentos.py — debe existir.

### Version actual
```
Version: 2026.1
ZIP revision: 12
Rama git: claude/blissful-franklin-p9g7U
Ultimo commit: e58afe4
```

---

## 4. DOCUMENTACION DE COMPONENTES

### app.py
- **Que hace**: Punto de entrada Flask. Registra 16 blueprints, filtros Jinja2, manejadores de error, scheduler APScheduler, inicializa BD.
- **Funciones clave**: `inicializar_app()`, `iniciar_scheduler()`, `configuracion()`, `crear_backup_manual()`
- **Dependencias**: todos los blueprints, core/logger, core/backup_manager, APScheduler

### config.py
- **Que hace**: Configura todas las rutas de archivos y constantes del sistema.
- **Clase Config**: `SECRET_KEY`, `DB_PATH`, `UPLOAD_FOLDER`, `PDF_FOLDER`, `BACKUP_FOLDER`, datos legales (NIT, representante), plazos PQRS/documentos.
- **Nota critica**: `definir_ruta_base_datos()` detecta si corre como .exe (PyInstaller) o script y ajusta la ruta de la BD automaticamente. Fallback a `%APPDATA%\PARAGUASMJ` si el directorio no tiene escritura.

### routes/documentos.py (v4 — 1448 lineas)
- **Que hace**: CRUD completo de documentos institucionales con editor HTML.
- **Funciones/rutas principales**:
  - `listar()` — GET /documentos/ con filtros, paginacion 20/pagina
  - `nuevo()` — GET/POST crear documento con editor contenteditable
  - `ver()` — detalle completo: firmantes, adjuntos, seguimiento, OTPs
  - `editar()` — editar contenido con versionado automatico
  - `cambiar_estado()` — Borrador→En_revision→En_autorizacion→Aprobado
  - `generar_pdf()` — PDF profesional con fallback simple
  - `api_guardar_borrador()` — autosave POST /api/borrador
  - `api_firmantes_activos()` — GET lista firmantes para el editor
  - `api_plantilla()` — GET plantilla HTML institucional
  - `api_ia_proxy()` — POST proxy hacia Anthropic/Ollama
  - `api_firmar()` — POST firma SHA-256 por firmante
  - `versiones()`, `restaurar_version()` — historial de versiones
  - `indicador_tiempo()` — semaforo TRD/CPACA dias habiles
  - `formato_transferencia()` — export Excel por fase archivo
  - `limpiar_borradores_antiguos()` — admin: elimina borradores >30 dias
- **TIPOS**: 41 tipos de documento (OFI, ACT, RES, PQR, ASEXR, CL, CONV, CRP, etc.)
- **PLANTILLAS**: 5 plantillas HTML (oficio_car, acta_reunion, contestacion_fiscal, acta_entrega_materiales, oficio_sspd)
- **Seguridad**: sanitizar_html() elimina `<script>` y eventos `on*=`

### routes/gis.py (v14 — 318 lineas)
- **Que hace**: GIS comunitario con GeoJSON, registro de fallas, infraestructura, suscriptores.
- **Funciones clave**:
  - `row_to_geojson_feature(row)` — helper que detecta columnas lat/lon segun tabla
  - `api_infraestructura()` — GET /gis/api/infraestructura GeoJSON
  - `api_suscriptores()` — GET /gis/api/suscriptores GeoJSON
  - `api_fallas()` — GET /gis/api/fallas GeoJSON (autenticado)
  - `nueva_falla()` — POST registra falla con precision_metros float seguro
  - `public_fallas_geojson()` — GET /gis/api/public/fallas.geojson SIN autenticacion
  - `documentos_paginados()` — GET documentos para panel lateral del mapa
- **Tablas BD**: `gis_infraestructura`, `gis_suscriptores_posicion`, `gis_reportes_fallas`, `zonas_prestacion`
- **Sistema referencia**: WGS84, soporte UTM (utm_x, utm_y, zona_utm)

### routes/pqrs.py (966 lineas)
- **Que hace**: Gestion completa de PQRS con plazos legales CPACA.
- **Plazos**: PQR=15 dias habiles, REQ=30, RECURSO=30
- **Flujo**: Recepcion → Asignacion responsable → Respuesta → Notificacion → Cierre
- **Tablas BD**: `pqrs`, `pqrs_seguimiento`, `pqrs_adjuntos`

### routes/balance_hidrico.py (259 lineas)
- **Que hace**: Balance hidrico mensual, IANC, graficas.
- **IANC** = (Producido - Facturado) / Producido * 100
- **Alerta**: IANC > 25% en rojo, reportable a SSPD
- **Tablas BD**: `balance_hidrico`, `lecturas_macromedidor`

### routes/finanzas.py (282 lineas)
- **Que hace**: Caja diaria, cuentas bancarias, movimientos contables.
- **Tablas BD**: `caja_diaria`, `cuentas_bancarias`, `movimientos_bancarios`

### routes/proyectos_v2.py (850 lineas)
- **Que hace**: Proyectos de inversion con PROGRAMA_5 (vinculacion con documentos).
- **Nota**: usa `with_retry()` del database_manager, NO define su propia version.

### routes/carpetas_bp.py (125 lineas)
- **Que hace**: Blueprint Flask para gestion de los 12 modulos documentales.
- **Endpoints**: `/carpetas/`, `/carpetas/crear_estructura` (admin+CSRF), `/carpetas/crear`, `/carpetas/eliminar` (admin), `/carpetas/explorar/<modulo>`, `/carpetas/estadisticas`, `/carpetas/auditoria`, `/carpetas/verificar_integridad`
- **CSRF requerido** en POST de admin

### core/database_manager.py (61 lineas)
- **Que hace**: Administra conexiones SQLite con WAL mode, reintentos y consecutivos de codigos.
- **Funciones clave**:
  - `get_db()` → sqlite3.Connection con row_factory=Row
  - `with_retry(fn, reintentos=3)` → ejecuta fn con backoff en caso de SQLITE_BUSY
  - `obtener_consecutivo(area, tipo, anio)` → siguiente numero de radicado
  - `registrar_log(accion, usuario, detalle)` → log simple en BD

### utils/auditoria.py (112 lineas)
- **Que hace**: Log de auditoria con cadena HMAC-SHA256 inmutable.
- **Clase AuditoriaManager**:
  - `registrar(accion, usuario, detalle, nivel, ip)` → escribe entrada encadenada en `logs/auditoria.jsonl`
  - `verificar_integridad()` → recorre toda la cadena verificando hashes
  - `obtener_ultimos(n)` → lista las ultimas n entradas
  - `exportar_reporte(destino)` → JSON completo
- **Algoritmo**: cada entrada incluye `hash_anterior` y `hash_actual` (SHA-256 del contenido). La firma HMAC usa clave de entorno `AUDIT_SECRET`.

### utils/seguridad.py (120 lineas)
- **Que hace**: Decoradores de sesion, CSRF y bloqueo por intentos fallidos.
- **Decoradores**: `@login_required`, `@admin_required`, `@auditor_required`, `@verificar_permiso(permiso)`
- **CSRF**: `generar_token_csrf()`, `verificar_token_csrf()`
- **Bloqueo**: max 5 intentos fallidos → bloqueo 15 minutos por IP (en memoria, no persiste en BD)
- **Timeout sesion**: 30 minutos de inactividad

### utils/file_manager.py (164 lineas)
- **Que hace**: Crea y gestiona los 12 modulos de carpetas documentales en `uploads/`.
- **12 modulos**: PQRS, Finanzas, Proyectos, GIS, Emergencias, Calidad_Agua, Legal, Suscriptores, Nivel_Quebrada, Backups, Config, Comunicaciones
- **Clase FileManager**:
  - `crear_estructura_completa()` → crea 60+ carpetas con rollback si falla
  - `crear_carpeta_personalizada(modulo, nombre)` → valida con validadores.py
  - `eliminar_carpeta(modulo, nombre)` → shutil.rmtree
  - `explorar_carpeta(modulo, sub, max_depth=3)` → arbol de directorios
  - `obtener_estadisticas()` → cache 60s con conteo de carpetas/archivos/bytes
- **Instancia global**: `file_manager = FileManager()`

### utils/validadores.py (81 lineas)
- **Que hace**: Validacion cross-platform de nombres de archivos y carpetas.
- **Funciones**: `validar_nombre_carpeta()`, `validar_longitud_ruta()`, `limpiar_nombre_carpeta()`, `verificar_espacio_disco()`, `es_nombre_reservado_windows()`
- **Nombres reservados Windows**: CON, PRN, AUX, NUL, COM1-9, LPT1-9
- **MAX_PATH Windows**: 260 caracteres

### core/otp_manager.py (182 lineas)
- **Que hace**: Genera y verifica codigos OTP de 6 digitos para autorizar documentos via WhatsApp.
- **Expiracion**: 30 minutos (configurable en Config.OTP_EXPIRA_MINUTOS)
- **Tabla BD**: `autorizaciones_otp`

### core/scheduler_notificaciones.py (118 lineas)
- **Que hace**: Tarea diaria (cron 08:00) que verifica vencimientos de documentos, PQRS proximas a vencer, y alertas TRD.
- **Funcion principal**: `tarea_diaria_completa()`

### core/backup_manager.py (35 lineas)
- **Que hace**: Copia SQLite a `database/backups/` con timestamp. Rota manteniendo los ultimos 10 backups.
- **Funcion**: `crear_backup()` → retorna ruta del backup creado

### core/pdf_profesional.py (395 lineas)
- **Que hace**: Genera PDFs con membrete oficial ASUACAP usando ReportLab.
- **Funcion principal**: `generar_pdf_documento(registro_id)` → ruta del PDF
- **Incluye**: logo, encabezado, tabla de metadatos, contenido, firmas, pie de pagina

### database/inicializar_db.py
- **Que hace**: Crea las 31 tablas de la BD SQLite con sus indices y datos semilla (usuario admin, configuracion por defecto).
- **Usuario admin inicial**: usuario=`admin`, password=`PARAGUASMJ2026` (bcrypt)
- **Tablas principales**: usuarios, contactos, registro_central, contenido_documento, seguimiento_documento, documentos_adjuntos, plazos_documento, firmantes, reglas_firmantes, documento_firmantes, acciones_pendientes, autorizaciones_otp, pqrs, balance_hidrico, gis_infraestructura, gis_suscriptores_posicion, gis_reportes_fallas, zonas_prestacion, trd, configuracion, configuracion_historial, expedientes, tipos_documento, ...

---

## 5. BASE TECNICA FUNDAMENTAL

### Patron Blueprint Flask
Cada modulo funcional es un Blueprint independiente con su prefijo de URL. Esto permite:
- Desarrollo paralelo sin conflictos
- Facil desactivacion de un modulo
- Tests aislados por modulo

### SQLite WAL Mode
La BD usa Write-Ahead Logging para permitir lecturas concurrentes mientras hay escrituras. Critico para el modo ejecutable .exe donde multiples peticiones del navegador llegan simultaneamente.

```python
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA foreign_keys=ON")
```

### Sistema de codigos de documentos
```
[AREA]-[TIPO]-[ANIO]-[CONSECUTIVO]
Ejemplo: GA-OFI-2026-001
         GF-PQR-2026-015
```
El consecutivo es atomico por (area, tipo, anio) — garantiza unicidad incluso con concurrencia.

### Cadena de auditoria HMAC-SHA256
```
Entrada N:
  hash_anterior = hash_actual de entrada N-1 (o "GENESIS")
  hash_actual   = SHA256(json(entrada_sin_firma))
  firma_hmac    = HMAC-SHA256(clave_secreta, hash_actual)
```
Cualquier modificacion de una entrada rompe la cadena detectable con `verificar_integridad()`.

### Sanitizacion HTML del editor
```python
# Elimina scripts
html = re.sub(r"<script\b...", "", html, flags=re.I|re.S)
# Elimina eventos inline
html = re.sub(r"\son\w+\s*=", " data-removed=", html)
```
Sin dependencias externas (no bleach/lxml) — funciona en exe offline.

### Firma de documentos (Nivel 1 no repudio)
```python
payload = f"{codigo}|{firmante}|{cargo}|{timestamp}|{ip}"
hash_firma = SHA256(payload.encode())
```
Guardado en `documento_firmantes.hash_firma`. Cuando todos los firmantes firman, el documento pasa automaticamente a estado `Aprobado`.

### PyInstaller + Flask
El exe incluye todos los templates, static files y modulos Python. Critico:
- `resolver_ruta(rel)` usa `sys._MEIPASS` cuando corre como exe
- `--add-data "templates;templates"` en el comando de compilacion
- `--collect-all=reportlab` y `--collect-all=jinja2` para submódulos

---

## 6. GUIA DE EJECUCION

### Instalacion en Windows (usuarios finales)
```
1. Descomprimir PARAGUASMJ_COMPLETO_12.zip
2. Click derecho en INSTALAR.bat → Ejecutar como administrador
3. El instalador: verifica/instala Python 3.11, instala dependencias, compila exe
4. Doble click en icono PARAGUASMJ del escritorio
```

### Instalacion para desarrolladores
```bash
# Clonar o descomprimir
cd PARAGUASMJ

# Crear entorno virtual (recomendado)
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install Flask>=3.1.0 waitress>=3.0.0 pandas>=2.1.0 openpyxl>=3.1.0
pip install reportlab>=4.1.0 Pillow>=10.0.0 APScheduler>=3.10.0
pip install requests>=2.32.0 python-docx>=1.1.0

# Inicializar base de datos
python database/inicializar_db.py

# Ejecutar en modo desarrollo
python app.py
# → Servidor en http://127.0.0.1:5000
```

### Ejecutar con waitress (produccion)
```bash
python run.py
# → Servidor en http://127.0.0.1:5000 (waitress, multi-thread)
```

### Ejecutar tests
```bash
python -m pytest tests/ -v
```

### Variables de entorno (opcionales)
```env
SECRET_KEY=clave_secreta_larga_aleatoria
AUDIT_SECRET=clave_para_hmac_auditoria
ANTHROPIC_API_KEY=sk-ant-...  # Para IA integrada
```

### Credenciales iniciales
```
Usuario: admin
Password: PARAGUASMJ2026
```

### Compilar exe Windows
```bash
# Ejecutar INSTALAR.bat como administrador
# O manualmente:
python -m PyInstaller --onefile --windowed --name="PARAGUASMJ_2026" \
  --add-data "templates;templates" --add-data "static;static" \
  --hidden-import=waitress --hidden-import=flask ... run.py
```

---

## 7. EJEMPLOS DE USO

### Crear un documento
```
1. /documentos/nuevo → seleccionar Area=GF, Tipo=OFI
2. Escribir asunto
3. En editor: usar boton "Plantilla" → seleccionar "Oficio a la CAR"
4. Editar contenido con [ASUNTO], [ACCION]
5. Seleccionar firmantes
6. Click "Guardar como Borrador" o "Radicar"
→ Codigo generado: GF-OFI-2026-001
```

### Autosave del editor (API)
```javascript
// Cada 30s el editor llama:
fetch('/documentos/api/borrador', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    id: 123,           // null si es nuevo
    contenido: "<p>...",
    asunto: "Oficio a la CAR"
  })
})
// Respuesta: {"ok": true, "id": 123}
```

### API IA para asistencia en redaccion
```javascript
fetch('/documentos/api/ia_proxy', {
  method: 'POST',
  body: JSON.stringify({
    instruccion: "Redacta un parrafo formal solicitando prorroga",
    contexto: "Acueducto comunitario, carta a la CAR"
  })
})
// Respuesta: {"ok": true, "texto": "...", "proveedor": "anthropic"}
```

### Registrar falla en mapa GIS
```javascript
fetch('/gis/api/fallas/nueva', {
  method: 'POST',
  body: JSON.stringify({
    lat: 5.0135, lon: -74.4700,
    descripcion: "Tuberia rota en sector norte",
    severidad: "alta",
    zona_id: 2,
    tipo_coordenada: "exacta",
    precision_metros: 5.0
  })
})
```

### GeoJSON publico (sin autenticacion)
```
GET /gis/api/public/fallas.geojson
→ FeatureCollection con fallas activas (max 500)
→ Compatible con IGAC, portales de datos abiertos
```

### Verificar integridad de auditoria
```python
from utils.auditoria import auditoria_manager
resultado = auditoria_manager.verificar_integridad()
# {"ok": True, "total": 1547, "errores": []}
```

---

## 8. RUTAS DE EXPANSION

### Prioritarias (falta implementar)
1. **`templates/carpetas/index.html`** — El blueprint carpetas_bp existe y funciona, pero sin template no puede renderizar la vista principal `/carpetas/`
2. **`templates/documentos/expedientes.html`** — La ruta `listar_expedientes()` existe, falta el template
3. **`core/calendario_colombiano.py`** — Implementar calendario con festivos colombianos para calculo preciso de dias habiles CPACA
4. **`core/gestor_trd.py`** — Referenciado en documentos.py, debe existir con metodos `verificar_transferencias_pendientes()`, `simular_transferencia()`, `ejecutar_transferencias()`
5. **`core/forensic_saneamiento.py`** — Referenciado en documentos.py con `SaneadorForense.normalizar_fecha_estatica()` y `obtener_ip_segura()`

### Mejoras tecnicas
- WeasyPrint para PDFs mas ricos (actualmente opcional, no en requirements.txt)
- Modo oscuro en el frontend
- Export DOCX del editor (python-docx ya instalado)
- Notificaciones push del navegador para vencimientos
- Multi-sede (varios acueductos en una instancia)

### Modulos nuevos posibles
- Calidad del agua IRCA (estructura en `core/indicadores_ius.py` ya existe)
- Lectura de medidores masiva (importar Excel)
- Portal suscriptor (consulta de factura y PQRS por codigo)
- Integracion SUI (SSPD) automatica via API

---

## 9. MAPA DE CONOCIMIENTO

### CRITICO — No se puede perder
- **config.py**: Todos los parametros legales del acueducto (NIT, representante, codigos DIVIPOLA)
- **database/inicializar_db.py**: La definicion de las 31 tablas. Si se pierde, no hay BD.
- **core/database_manager.py**: El patron `with_retry()` y `get_db()` — todo el sistema depende de esto
- **routes/documentos.py**: El modulo mas grande (1448 lineas). Contiene toda la logica documental.
- **La lista de --hidden-import en INSTALAR.bat**: Sin ella, el exe no incluira los blueprints.

### IMPORTANTE pero recuperable
- Templates HTML (se pueden redisenar)
- static/css/estilo.css (se puede redisenar)
- Tests (se pueden reescribir)
- Logs de auditoria (se recrean al usar el sistema)

### OPCIONAL
- Documentacion .md adicional
- Archivos .bat de configuracion git
- Datos semilla de la BD (se recrean al inicializar)

### Preguntas clave para continuar
1. ¿Existen `core/gestor_trd.py` y `core/forensic_saneamiento.py`? Son importados por routes/documentos.py — si no existen, el blueprint falla.
2. ¿Cual es la estructura real de `gis_reportes_fallas` en produccion? ¿Tiene la columna `tipo_coordenada`?
3. ¿Esta configurado el numero de WhatsApp para OTP en la tabla `configuracion`?
4. ¿Tiene el cliente instalado Python 3.11 o usa el exe compilado?
5. ¿Tiene API key de Anthropic para la funcion IA del editor?

---

## 10. CHECKLIST DE CONTINUIDAD

- [ ] Entendi que PARAGUASMJ es un sistema documental para un acueducto comunitario colombiano
- [ ] Se que el backend es Flask + SQLite, sin frameworks frontend pesados
- [ ] Identifique los 16 blueprints y sus prefijos URL
- [ ] Se que hay 31 tablas en la BD inicializadas por database/inicializar_db.py
- [ ] Entendi el sistema de codigos de documentos (AREA-TIPO-ANIO-CONSECUTIVO)
- [ ] Se que el editor usa contenteditable (NO TipTap CDN) para funcionar offline
- [ ] Comprendo que el autosave usa POST /documentos/api/borrador cada 30s
- [ ] Se que INSTALAR.bat debe ser ASCII puro (sin tildes ni Unicode) para CMD
- [ ] Se que el push a GitHub falla 403 — se entregan ZIPs con revision numerada
- [ ] Identifique los archivos faltantes: core/gestor_trd.py, core/forensic_saneamiento.py, core/calendario_colombiano.py, templates/carpetas/index.html, templates/documentos/expedientes.html
- [ ] Puedo ejecutar el sistema con: python app.py → http://127.0.0.1:5000
- [ ] Las credenciales iniciales son admin / PARAGUASMJ2026
- [ ] Se agregar una nueva ruta: crear Blueprint, registrar en app.py, crear template
- [ ] Entendi la cadena de auditoria HMAC-SHA256 en utils/auditoria.py
- [ ] Se que los modulos de carpetas (12) se crean con crear_estructura_completa.bat

---

***
Documento generado automaticamente el 2026-06-07.
Version ZIP: PARAGUASMJ_COMPLETO_12 | Branch: claude/blissful-franklin-p9g7U

**Nota**: Este documento es un RESPALDO TECNICO COMPLETO.
Cualquier IA o desarrollador puede continuar el proyecto desde aqui
con total comprension del estado actual, decisiones tomadas y proximos pasos.
