# CHANGELOG — PARAGUASMJ

## [2026.1.0] — 2026-05-24
### Primera entrega completa
- 31 tablas SQLite con indices optimizados
- 9 Blueprints Flask (auth, dashboard, documentos, pqrs, comunicaciones, proyectos, GIS, balance, api)
- Templates HTML Bootstrap 5.3 responsivos
- OTP WhatsApp via CallMeBot para firmas digitales
- Exportacion PDF con ReportLab (sin GTK)
- Reportes Excel institucionales para CAR/SSPD (3 hojas)
- GIS Leaflet offline con APIs GeoJSON
- Indicadores CRA: IANC, IRAC calculados automaticamente
- Scheduler APScheduler: notificaciones a las 8:00 AM + backup diario
- Configuracion dinamica desde interfaz web
- Blindaje DB_PATH para entornos sin permisos de escritura
- Compatible con PyInstaller para distribucion .exe

## [2026.3.0] — 2026-05-24 — Mejoras PROGRAMA_1 + PROGRAMA_2

### Nuevos módulos
- **core/indicadores_ius.py** — Todos los indicadores normativos: IANC, IPAA, IMA, EET,
  POACg, Continuidad, Cobertura, IRAC, IUS compuesto (CRA Res. 906/2019)
- **core/reportes_sspd.py** — FC15 para XBRL Express SSPD, Hoja IUS mensual,
  Balance Hídrico CAR/PUEAA (estructura exacta exigida)
- **core/pdf_profesional.py** — PDFs con membrete completo (logo, eslogan, NIT),
  márgenes A4 correctos (2.5/2cm), tipografía jerarquizada, numeración X/Y,
  actas de entrega de materiales con totales automáticos
- **core/email_manager.py** — Envío SMTP del PUEAA a CAR (sau@car.gov.co),
  notificaciones de cambio de estado PQRS, historial de envíos
- **routes/finanzas.py** — Caja menor + Bancos + Movimientos bancarios con cálculo
  de saldo anterior (patrón VBA→Python del PROGRAMA_1)
- **routes/reportes_normativos.py** — Panel unificado FC15, Hoja IUS, Balance CAR,
  Reporte trimestral, Envío PUEAA, Backup

### Base de datos (nuevas tablas)
- `juego_config`, `juego_fotos`, `juego_puntos` — Módulo reciclaje comunitario
- `reportes_semanales` — Flujo borrador→aprobación→PDF (PROGRAMA_2)
- `infraestructura_pueaa` — Componentes del sistema con estado para PUEAA
- `aforos` — Registro de aforos en puntos de la red
- `actividades_pueaa` — 7 proyectos PUEAA con avance quinquenal
- `registros_irca` — Calidad del agua (IRCA por mes)
- Columnas `bloqueado`, `intentos_fallidos` en `usuarios` (seguridad PIN)

### Nuevos parámetros de configuración
- `longitud_red_km`, `horas_servicio_dia`, `empleados_operativos`
- `total_viviendas`, `kwh_anuales`, `macromedidores_func`, `total_tramos`
- `irca_ultimo`, `caudal_concesionado_ls`, `correo_car`, `eslogan`

### Menú actualizado
- Nuevo item **Finanzas** (Caja Menor, Bancos, Movimientos)
- Nuevo item **Reportes CAR/SSPD/CRA** (FC15, Hoja IUS, Balance, PUEAA)

## [2026.4.0] — 2026-05-25 — PROGRAMA_3 + PROGRAMA_4 completos

### PROGRAMA_3 — Auditoría y Gestión de Usuarios
- **utils/audit.py** — log_action() + decorador @audit con IP, User-Agent, timestamp
- **routes/auditoria.py** — Panel logs paginados (GET/filtros/export Excel), stats en tiempo real
- **routes/auditoria.py** — CRUD usuarios con foto (upload, preview circular, desbloqueo)
- **templates/auditoria/panel.html** — Tabla logs autorefresh 30s, badges por acción, filtros
- **templates/auditoria/usuarios.html** — Modal crear/editar usuario con foto preview
- **BD:** audit_log, autorizaciones_extendidas, foto_path en usuarios, bloqueado/intentos_fallidos

### PROGRAMA_4 — Proyectos con Gantt
- **routes/proyectos_v2.py** — API REST completa: proyectos CRUD, tareas, Gantt, costos, ingresos, riesgos, metas PUEAA/PSMV
- **templates/proyectos2/panel.html** — Grid de proyectos con KPIs, modal detalle con 6 tabs:
  - 📊 Resumen: avance, saldo financiero, acciones rápidas
  - ✅ Tareas: slider de avance, cambio de estado inline
  - 📅 Gantt: Frappe Gantt CDN con dependencias FS/SS/FF/SF
  - 💰 Costos/Ingresos: tablas separadas con saldo automático
  - ⚠️ Riesgos: semáforo por probabilidad/impacto, actualizar estado
  - 🎯 Metas PUEAA/PSMV: anuales y semestrales, marcar cumplidas
- **BD:** tareas_proyecto, dependencias, costos_reales, ingresos, riesgos_proyecto, metas_proyecto

### Correcciones técnicas
- Schema BD reconciliado: pk_proyecto_id, fecha_inicio, fecha_limite, presupuesto, valor_ejecutado
- Blueprints fin_bp, rep_bp, aud_bp, proy2_bp registrados correctamente en app.py
- url_for proyectos2.panel → ruta directa /proyectos2/ para compatibilidad
- Suite de pruebas: **16/16 (100%)** pasadas

## [2026.5.0] — 2026-05-25 — PROGRAMA_5 + correcciones

### PROGRAMA_5 — Integración Documentos ↔ Proyectos
- **documentos_proyecto** — tabla N:M (documentos ↔ proyectos) con tipo de relación (soporte/entregable/acta/contrato)
- **meta_documentos** — documentos soporte por meta PUEAA/PSMV para trazabilidad normativa ante la CAR
- **API `/proyectos2/api/<pid>/documentos`** — asociar, listar y desasociar documentos de un proyecto
- **API `/proyectos2/api/metas/<mid>/documentos`** — documentos soporte por meta específica
- **API `/proyectos2/api/buscar_documento`** — búsqueda de documentos por código/asunto para asociar
- **API `/proyectos2/api/<pid>/informe_avance`** — Excel con 4 hojas: Resumen, Metas+docs soporte, Tareas, Documentos asociados
- **Tab "Documentos"** en el modal de detalle de proyecto (7ma pestaña)
- **Editor de documentos** — nuevo campo "Proyecto relacionado" con selector dinámico
- **routes/documentos.py** — endpoints `/api/buscar` y `/api/proyecto/<pid>` para la asociación desde el editor
- **Diagrama de flujo**: Crear documento → seleccionar proyecto → queda asociado automáticamente

### Correcciones de arquitectura (PROG_3/4 consolidados)
- Schema BD reconciliado definitivamente con los nombres reales de columnas
- Blueprint proy2_bp registrado correctamente con rutas verificadas
- Suite de pruebas: **18/18 (100%)** pruebas pasadas

## [2026.7.0] — 2026-05-26 — PROGRAMA_7 + PEC Corregido

### Fórmula PEC ASUACAP implementada (datos reales del pec.doc)
- **Fórmula exacta:** V = (Ia×0.10 + It×0.80 + Ic×0.00 + Iq×0.10) × P
- **Umbrales:** Alta ≥ 0.50 | Media ≥ 0.25 | Baja < 0.25
- **10 riesgos reales R-01..R-10** cargados con valoraciones verificadas
- Todos clasificados como **Alta** (Salud del Sistema = 0%)
- Protocolos de alerta quebrada: Verde/Amarillo/Naranja/Rojo con acciones exactas del PEC

### Generación de documentos PEC
- **Excel Listado de Riesgos:** 3 hojas (completo + por prioridad + parámetros)
  - Fórmula y ponderaciones visibles en hoja "Parámetros PEC"
  - Semáforo de colores automático (rojo/amarillo/verde)
- **Word PEC anual actualizable por año:**
  - Portada institucional con logo y eslogan
  - Metodología de valoración con fórmula
  - Protocolo de alertas por nivel (verde/amarillo/naranja/rojo)
  - Tabla de riesgos completa con plan de respuesta
  - Inventario de recursos por categoría
  - Pie de firmas (Representante Legal + Jefe Operativo)

### PROGRAMA_7 — Compilación a .exe Windows 11
- requirements.txt con python-docx incluido
- run.py con apertura automática del navegador (waitress producción)
- build/build.bat con 5 pasos, todos los --hidden-import necesarios
- Soporte PyInstaller --onefile --windowed

### Tests: 15/15 (100%)
