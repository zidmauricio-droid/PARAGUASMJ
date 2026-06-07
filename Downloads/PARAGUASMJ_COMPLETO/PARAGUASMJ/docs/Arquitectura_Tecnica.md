# Arquitectura Tecnica — PARAGUASMJ

## Stack tecnologico
| Capa | Tecnologia |
|------|-----------|
| Backend | Python 3.11+ / Flask 3.0 |
| Base de datos | SQLite 3 (WAL mode) |
| Frontend | Bootstrap 5.3 + Bootstrap Icons |
| Editor de texto | TinyMCE self-hosted (offline) |
| Mapas | Leaflet.js self-hosted (offline) |
| PDF | ReportLab 4.x |
| Excel | pandas + openpyxl |
| Notificaciones WhatsApp | CallMeBot API |
| Scheduler | APScheduler 3.x |
| Empaquetado | PyInstaller 6.x |
| Instalador Windows | Inno Setup |

## Estructura de consecutivos
Formato: `{AREA}-{TIPO}-{ANO}-{NNN}`

Areas: GA (Ambiental), GC (Comercial), GF (Financiera),
       GE (Estrategica), GL (Legal), GT (Tecnica)

## Tablas criticas (31)
usuarios, contactos, registro_central, contenido_documento,
seguimiento_documento, documentos_adjuntos, plazos_documento,
firmantes, reglas_firmantes, autorizaciones_otp, acciones_pendientes,
pqrs, comunicaciones_recibidas, proyectos, actividades,
presupuesto_rubros, cotizaciones, ordenes_compra_productos,
tareas, ordenes_trabajo, ordenes_salida, actas_ejecucion,
lecturas_macromedicion, balance_hidrico, indicadores_mensuales,
riesgos, bancos, movimientos_financieros, caja_chica,
zonas_prestacion, gis_infraestructura, gis_suscriptores_posicion,
gis_reportes_fallas, configuracion, configuracion_historial
