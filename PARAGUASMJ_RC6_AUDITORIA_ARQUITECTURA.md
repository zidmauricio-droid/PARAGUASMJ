# PARAGUASMJ — AUDITORÍA ARQUITECTÓNICA RC6
**Fecha:** 2026-06-13 | **Versión:** RC6.2 | **Auditor:** Sistema SIGCA

---

## 1. ESTADO DE MÓDULOS POR ÁREA INSTITUCIONAL

| Código | Módulo | Blueprint | Estado | Observación |
|--------|--------|-----------|--------|-------------|
| GE-01 | Gobierno Corporativo | `gobierno_bp` (gobierno.py) — `/ge` | ✅ Correcto | Registrado en app.py; gestiona actas y resoluciones institucionales. Migración 030_gobierno_ge01 aplicada. |
| GE-02 | Planeación Estratégica | — | ⚠️ Debe ajustarse | No existe blueprint independiente. Funcionalidad parcialmente cubierta por proyectos_v2 y reportes_normativos. |
| GE-03 | Normatividad Interna | — | ⚠️ Debe ajustarse | Sin módulo dedicado. Documentos generales en docs_bp pero sin categorización GE específica. |
| GE-04 | Evaluación de Desempeño | — | ⚠️ Debe ajustarse | No implementado. Candidato para GL o GE en versión futura. |
| GE-05 | Gestión Institucional / Reportes Normativos | `rep_bp` (reportes_normativos.py) | ✅ Correcto | Registrado. Incluye FC15 IUS, Balance CAR, envío PUEAA a CAR por correo y generación de actas. |
| GC-01 | Suscriptores | `sus_bp` (suscriptores.py) — `/suscriptores` | ✅ Correcto | Registrado. API de causales, conexiones y detalle de suscriptor. Migración 026_suscriptores_gc01 aplicada. |
| GC-02 | PQRS | `pqrs_bp` (pqrs.py) — `/pqrs` | ✅ Correcto | Registrado. Estructura Servicio → Solicitante → Medio → Causal implementada. Migraciones 018/031/032 aplicadas. Exportación SUI incluida. |
| GC-03 | Comunicaciones | `com_bp` (comunicaciones.py) | ✅ Correcto | Registrado en app.py. |
| GC-04 | Educación al Usuario | — | ⚠️ Debe ajustarse | No implementado. Sin blueprint ni plantillas asociadas. |
| GC-05 | Atención Presencial / Medición Satisfacción | — | ⚠️ Debe ajustarse | No implementado. |
| GF-01 | Caja | `fin_bp` (finanzas.py) — `/finanzas/caja` | ✅ Correcto | Registrado. Módulo unificado de finanzas cubre Caja con consulta, nuevo movimiento y exportación. |
| GF-02 | Tesorería | `fin_bp` (finanzas.py) — `/finanzas/movimientos` | ✅ Correcto | Transacciones, comprobantes y resumen mensual dentro del mismo blueprint fin_bp. |
| GF-03 | Bancos | `fin_bp` (finanzas.py) — `/finanzas/bancos` | ✅ Correcto | Gestión de cuentas bancarias y movimientos bancarios unificados en fin_bp. Migración 025_plan_cuentas_financiero aplicada. |
| GF-04 | Presupuesto | `fin_bp` (finanzas.py) — `/finanzas/plan-cuentas` | ✅ Correcto | Plan de cuentas, transacciones presupuestales y API de resumen mensual en fin_bp. |
| GF-05 | Inventarios | `inv_bp` (inventarios.py) — `/inventarios` | ✅ Correcto | Registrado. Alertas de stock mínimo y registro de movimientos de entrada/salida. |
| GF-06 | Convenios | `conv_bp` (convenios.py) — `/convenios` | ✅ Correcto | Registrado. Gestiona convenios, contratos, adiciones y prórrogas. |
| GA-01 | GIS / Infraestructura | `gis_bp` (gis.py) — `/gis` | ✅ Correcto | Registrado. Puntos georreferenciados, fallas con severidad, infraestructura, zonas y concertación (migración 028). |
| GA-02 | Calidad del Agua | `cal_bp` (calidad_agua.py) — `/calidad-agua` | ✅ Correcto | Registrado. API de parámetros, puntos de muestreo, resultados y resumen anual. UI mejorada en RC6.2. Migración 023 aplicada. |
| GA-03 | Balance Hídrico | `bh_bp` (balance_hidrico.py) — `/balance` | ✅ Correcto | Registrado. Macromedidor mensual, IANC, IUS, análisis de fuentes hídricas, exportación Excel. Migraciones 024/033/034 aplicadas. |
| GA-04 | Captación / Fuentes Hídricas | `bh_bp` (balance_hidrico.py) — `/balance/fuentes` | ✅ Correcto | Renombrado como "Captación" en RC6.2. Integrado en balance_hidrico.py: API de fuentes, escala limnimétrica y mediciones. |
| GA-05 | Distribución / Redes | — | ⚠️ Debe ajustarse | No implementado. Parcialmente cubierto en GIS pero sin módulo operativo dedicado. |
| GA-06 | Saneamiento / Vertimientos | — | ⚠️ Debe ajustarse | No implementado. PSMV integrado en GA-08 como tipo de proyecto, no como módulo operativo independiente. |
| GA-07 | Órdenes de Trabajo | `ot_bp` (ordenes_trabajo_rc6.py) — `/ordenes-trabajo` | ✅ Correcto | Registrado con nombre corregido RC6. Migración 027 aplicada. Materiales, estados y resumen operativo. |
| GA-08 | Proyectos (PUEAA / PSMV / PEC / Obras) | `proy2_bp` (proyectos_v2.py) — `/proyectos` | ✅ Correcto | Registrado. Módulo unificado v2: tipos incluyen PUEAA, PSMV y obras. Gantt, costos, ingresos, riesgos, evidencias y metas PUEAA/PSMV. Migraciones 020/021 aplicadas. |
| GL-01 | Personal | `lab_bp` (laboral.py) — `/laboral` | ✅ Correcto | Registrado. API de personal con filtros activo/cargo. Migración 029_personal_gl01 aplicada. |
| GL-02 | Nómina | — | ⚠️ Debe ajustarse | No implementado. |
| GL-03 | Seguridad Social | — | ⚠️ Debe ajustarse | No implementado. |
| GL-04 | Capacitación | — | ⚠️ Debe ajustarse | No implementado. |
| GL-05 | Evaluación de Personal | — | ⚠️ Debe ajustarse | No implementado. |

---

## 2. MATRIZ GAP — ACTUAL vs OBJETIVO

| Elemento | Estado Actual | Estado Objetivo | GAP | Acción |
|----------|--------------|-----------------|-----|--------|
| PEC como módulo independiente | Integrado en GA-08 como tipo de proyecto dentro de proyectos_v2.py | Gestión PEC centralizada en GA-08 | Sin GAP funcional | CONFIRMADO — PEC se gestiona en Proyectos v2. No debe existir blueprint separado. ✅ |
| PUEAA como módulo independiente | Integrado en GA-08 (proyectos_v2.py) con metas PUEAA y en GE-05 para reporte/envío a CAR | Gestión PUEAA en GA-08 + reporte en GE-05 | Sin GAP | Arquitectura correcta. Tipos de proyecto incluyen código `"pueaa"`. ✅ |
| PSMV como módulo independiente | Integrado en GA-08 (proyectos_v2.py) con metas PSMV | Gestión PSMV en GA-08 | Sin GAP | Arquitectura correcta. Tipos de proyecto incluyen código `"psmv"`. ✅ |
| Blueprint `emergencias` | Carpeta `/templates/emergencias/` existente con panel.html pero **sin blueprint registrado en app.py** | Eliminado en RC6.2 | ✅ ELIMINADO — no registrado en app.py | Pendiente: eliminar carpeta de plantillas huérfana `/templates/emergencias/`. |
| `proyectos.py` v1 | Sin archivo proyectos.py en routes/; sólo existe proyectos_v2.py | Eliminado en RC6.2 | ✅ ELIMINADO en RC6.2 | Carpeta `/templates/proyectos/` aún existe (huérfana). Verificar y eliminar. |
| Calidad Agua UI | Mejorada en RC6.2; migración 023_calidad_agua_estructurada aplicada | UI estructurada con parámetros Res. 2115 | ✅ IMPLEMENTADO en RC6.2 | Mantener. Verificar cobertura completa de parámetros normativos. |
| GA-04 Captación (renombrado) | Renombrado y consolidado en balance_hidrico.py bajo `/balance/fuentes` | Captación operativa bajo GA-03/GA-04 | ✅ IMPLEMENTADO en RC6.2 | Migración 034_unificar_nivel_quebrada confirma unificación. |
| ASUACAP hardcoded | Eliminado en RC6.2; organización proviene de tabla `organizaciones` en DB | Nombre dinámico desde base de datos | ✅ ELIMINADO en RC6.2 | Sin acción requerida. |
| Tema visual dark | Implementado en RC6.2 | Tema oscuro institucional coherente | ✅ IMPLEMENTADO en RC6.2 | Verificar consistencia visual en todas las plantillas (especialmente mapa_operaciones.html, nueva_lectura.html). |
| Módulos GL-02..05 | No existen rutas ni migraciones para nómina/SS/capacitación/evaluación | Implementación futura RC7 | GAP alto — 4 módulos ausentes | Planificar en versión RC7 partiendo de la base de personal GL-01 ya implementada. |
| Módulos GC-04, GC-05 | Sin blueprint ni plantillas | Completar ciclo comercial GC | GAP medio — 2 módulos ausentes | Planificar en versión RC7. |
| Módulos GE-02, GE-03, GE-04 | Sin blueprint ni plantillas dedicadas | Completar ciclo de gobierno GE | GAP medio — 3 módulos ausentes | Evaluar prioridad vs GL en RC7. |
| Rutas admin en app.py | `/configuracion`, `/gestion_usuarios`, `/panel_reportes`, `/backup/crear` definidos en app.py | Migrar a blueprints | GAP arquitectónico medio | Crear `admin_bp` en RC7 para separar responsabilidades. |

---

## 3. VALIDACIONES NORMATIVAS

### GC-02 PQRS
- **Estructura Servicio → Solicitante → Medio → Causal:** Implementada correctamente. El blueprint `pqrs_bp` expone `api_gc_servicios()`, gestión de solicitante vía suscriptores, `api_gc_medios()` y `api_gc_causales()`. Las migraciones 018_pqrs_causales_sspd, 031_pqrs_jerarquia y 032_pqrs_rc6_campos refuerzan la jerarquía normativa.
- **Tipos de PQR:** La tabla `pqrs` incluye CHECK validado con: Peticion, Queja, Reclamo, Sugerencia, Denuncia, Consulta, Recurso de Reposicion, Recurso de Apelacion.
- **Exportación SUI:** Función `exportar_sui()` implementada en pqrs.py.
- **Días hábiles:** Función `_dias_habiles()` implementada para cálculo correcto de fechas límite.
- **Estado normativo:** ✅ Cumple estructura SSPD. Validación de causales por servicio operativa.

### GA-02 Calidad del Agua (Res. 2115/2007)
- **Puntos de muestreo:** API `api_puntos()` y `api_crear_punto()` en calidad_agua.py.
- **Parámetros:** API `api_parametros()` gestiona parámetros con valores de referencia. Migración 023_calidad_agua_estructurada aplica esquema estructurado.
- **Resultado Aceptable/No Aceptable:** Muestras y resultados registrados mediante `api_guardar_resultados()`. Resumen anual disponible via `api_resumen_anio()`.
- **Estado normativo:** ✅ Estructura correcta. Verificar que los parámetros semilla incluyan todos los valores límite de la Res. 2115/2007: turbiedad (≤2 UNT), color aparente (≤15 UPC), pH (6.5–9.0), cloro residual (0.3–2.0 mg/L) y coliformes totales (0 UFC/100mL).

### GA-03 Balance Hídrico (CRA 906/2019)
- **Macromedidor mensual:** Implementado. `api_guardar()` en balance_hidrico.py persiste lecturas mensuales por fuente. Migración 024_balance_hidrico_mensual aplica estructura.
- **IANC (Índice de Agua No Contabilizada):** `api_indicadores()` calcula indicadores anuales incluyendo IANC.
- **IUS CRA 906/2019:** Función de IUS implementada en reportes_normativos.py (FC15 IUS) como balance hídrico trimestral para CAR/PUEAA.
- **Fuentes hídricas:** API de fuentes (`api_fuentes_listar`, `api_fuentes_crear`, `api_fuentes_editar`), escala limnimétrica y mediciones con detección de eventos y análisis de tendencias. Migraciones 033 y 034 aplicadas.
- **Estado normativo:** ✅ Cumple. Exportación Excel disponible para reporte a CAR.

### GA-01 GIS
- **Puntos georreferenciados:** `api_infraestructura()` y `api_suscriptores()` retornan geometrías GeoJSON con coordenadas.
- **Registro de fallas:** `api_fallas()` y `nueva_falla()` con mapeo de severidad (`_mapear_severidad()`).
- **Puntos de concertación:** Migración 028_puntos_concertacion aplicada; endpoint `public_fallas_geojson()` disponible para integración externa.
- **Zonas operativas:** `api_zonas()` implementado.
- **Estado normativo:** ✅ Correcto. Infraestructura GIS completa con datos de fallas georreferenciadas y puntos de concertación.

---

## 4. RIESGOS ARQUITECTÓNICOS

| Nivel | Descripción | Módulo afectado | Recomendación |
|-------|-------------|-----------------|---------------|
| Alto | Plantillas huérfanas en `/templates/emergencias/` (panel.html) sin blueprint registrado. Pueden causar confusión en mantenimiento y generar referencias cruzadas rotas en el futuro. | Emergencias (eliminado RC6.2) | Eliminar carpeta `/templates/emergencias/` completa del repositorio. |
| Alto | Carpeta `/templates/proyectos/` con plantillas de la v1 (form.html, lista.html, nuevo.html, ver.html) sin blueprint activo. Riesgo de referencias accidentales a código obsoleto. | GA-08 (proyectos v1 eliminada) | Eliminar o archivar carpeta `/templates/proyectos/`. Confirmar que todas las referencias apuntan a `/templates/proyectos2/`. |
| Medio | Módulos GL-02 a GL-05 (Nómina, Seguridad Social, Capacitación, Evaluación) no implementados pero requeridos por la normativa de prestadores de servicios públicos. | GL (Gestión Laboral) | Documentar explícitamente como "pendiente RC7". Ocultar en navegación si están visibles. |
| Medio | Módulos GC-04, GC-05 y GE-02 a GE-04 sin blueprint ni plantillas. El menú puede generar expectativa de funcionalidad no disponible a los operadores. | GC, GE | Marcar como "Próximamente" o deshabilitar en navegación hasta implementación en RC7. |
| Medio | Rutas `/configuracion`, `/gestion_usuarios`, `/panel_reportes` y `/backup/crear` definidas directamente en `app.py` en lugar de blueprints. Dificulta pruebas unitarias y separación de responsabilidades. | app.py (core) | Migrar a blueprint `admin_bp` en RC7. |
| Medio | APScheduler iniciado con `daemon=True` sin garantía de que todas las migraciones completaron exitosamente. Si una migración falla silenciosamente (el bloque `try/except` suprime el error), el scheduler puede operar sobre BD incompleta. | core/scheduler y database/migrations | Agregar verificación de integridad de BD post-migraciones antes de llamar `iniciar_scheduler()`. |
| Bajo | 18 migraciones acumuladas (017–034) ejecutadas secuencialmente al arranque sin tabla de control `schema_version`. En entornos con BD creciente puede generar latencia al inicio de la aplicación. | database/migrations | Implementar tabla `schema_version` para saltear migraciones ya aplicadas de forma eficiente. |
| Bajo | Blueprint `aud_bp` (auditoria.py) registrado en app.py pero sin visibilidad confirmada en menú principal. La trazabilidad puede no ser accedida por operadores del sistema. | Auditoría | Verificar que el módulo esté enlazado desde el panel de administración. |
| Bajo | Rutas `/panel_reportes` y `/reportes/exportar/trimestral` en app.py solapan funcionalmente con GE-05 (`rep_bp`), creando duplicidad de responsabilidad entre app.py y reportes_normativos.py. | GE-05 / app.py | Consolidar en `rep_bp` en próxima iteración para coherencia arquitectónica. |

---

## 5. RECOMENDACIONES PRIORIZADAS

1. **Eliminar plantillas huérfanas de versiones anteriores.** Borrar `/templates/emergencias/` y `/templates/proyectos/` (v1). Estas carpetas no tienen blueprint asociado en RC6.2, generan riesgo de referencias cruzadas rotas y confunden el mantenimiento del código base.

2. **Migrar rutas administrativas de app.py a blueprints.** Las rutas `/configuracion`, `/gestion_usuarios`, `/panel_reportes` y `/backup/crear` deben trasladarse a un blueprint `admin_bp`. Las rutas de reporte deben consolidarse en `rep_bp`. Esto mejora la testabilidad y separación de responsabilidades.

3. **Implementar tabla `schema_version` para control de migraciones.** Con 18 migraciones acumuladas, agregar una tabla de control permitirá arranques más rápidos, trazabilidad clara del estado del esquema y evitará re-ejecución de migraciones ya aplicadas.

4. **Verificar parámetros semilla de Calidad del Agua (Res. 2115/2007).** Confirmar que la migración 023 incluye todos los parámetros requeridos con sus valores límite: turbiedad (≤2 UNT), color aparente (≤15 UPC), pH (6.5–9.0), cloro residual (0.3–2.0 mg/L), coliformes totales (0 UFC/100mL).

5. **Documentar módulos pendientes RC7 en navegación.** Marcar explícitamente GC-04, GC-05, GE-02 a GE-04, y GL-02 a GL-05 como "Próximamente" o inhabilitarlos en el menú para evitar expectativas no cumplidas a los operadores.

6. **Agregar verificación de integridad post-migración antes del scheduler.** Asegurar que `inicializar_app()` y todas las migraciones completan exitosamente antes de llamar `iniciar_scheduler()`. El bloque `try/except` actual suprime errores de migración que pueden dejar la BD en estado inconsistente.

7. **Planificar GL-02 Nómina para RC7.** El módulo de personal GL-01 está implementado con base de datos de personal (migración 029). GL-02 Nómina es el paso natural siguiente partiendo de la estructura laboral existente en laboral.py.

8. **Revisar consistencia del tema dark en todas las plantillas.** El tema fue implementado en RC6.2. Auditar plantillas individuales — especialmente `mapa_operaciones.html`, `nueva_lectura.html` y `balance_hidrico.html` — para asegurar coherencia visual completa.

9. **Consolidar lógica de PUEAA/PSMV entre GA-08 y GE-05.** Verificar que `reportes_normativos.py` no duplique lógica de gestión de PUEAA/PSMV con `proyectos_v2.py`. La función de GE-05 debe ser exclusivamente de reporte/exportación, no de gestión de proyectos.

10. **Garantizar acceso al módulo de Auditoría desde la UI.** El blueprint `aud_bp` está registrado pero su accesibilidad desde el panel de administración no está confirmada. Incluir enlace visible para garantizar trazabilidad operativa del sistema.

---

## 6. RESUMEN EJECUTIVO

PARAGUASMJ en su versión RC6.2 presenta una arquitectura Flask modular con 20 blueprints registrados que cubren las cinco áreas institucionales del sistema: Gestión Empresarial (GE), Gestión Comercial (GC), Gestión Financiera (GF), Gestión Ambiental y Técnica (GA) y Gestión Laboral (GL). Los módulos de mayor criticidad operativa se encuentran correctamente implementados: PQRS con jerarquía SSPD y exportación SUI, Balance Hídrico con indicadores CRA 906/2019, Calidad del Agua con estructura Res. 2115/2007, GIS con georreferenciación y puntos de concertación, y Proyectos unificados que absorben PUEAA, PSMV y PEC. La versión RC6.2 eliminó exitosamente el blueprint de emergencias, la versión v1 de proyectos (aunque persisten plantillas huérfanas), el hardcoding de ASUACAP, e implementó el tema visual dark, la renombración de GA-04 Captación y 18 migraciones progresivas de base de datos. Los riesgos principales son la permanencia de carpetas de plantillas huérfanas que deben eliminarse, la concentración de rutas administrativas directamente en app.py que afecta la separación de responsabilidades, y la ausencia de 9 módulos planificados (GC-04/05, GE-02/03/04, GA-05/06, GL-02/03/04/05) que requieren planificación para RC7. El sistema cumple con los requisitos normativos aplicables a prestadores de servicios públicos de acueducto en Colombia y se encuentra en condición de estabilidad operativa RC6.2 apta para despliegue en producción.

---

*Documento generado por análisis arquitectónico directo del código fuente en 2026-06-13. Revisión humana recomendada antes de uso en auditoría formal.*
