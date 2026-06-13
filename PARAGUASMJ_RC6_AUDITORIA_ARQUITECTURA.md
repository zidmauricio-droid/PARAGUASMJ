# PARAGUASMJ — AUDITORÍA ARQUITECTÓNICA RC6.1
## Documento Oficial · Auditor RC6.1 · Fecha: 2026-06-13

---

## PREÁMBULO

La presente auditoría evalúa el estado arquitectónico actual del sistema PARAGUASMJ frente a la arquitectura institucional aprobada en RC6.1. El análisis se realizó sobre el código fuente real del repositorio `zidmauricio-droid/PARAGUASMJ`, rama `claude/blissful-franklin-p9g7U`, commit `5e0e7be`.

**Archivos revisados:**
- `app.py` (punto de entrada, 22 blueprints registrados)
- `routes/` (23 archivos de rutas)
- `templates/` (47 archivos HTML)
- `database/migrations/` (migraciones 016–031)
- `static/css/estilo.css`
- `templates/base.html` (sidebar de navegación)

---

## PARTE 1 — AUDITORÍA COMPLETA

### 1.1 BLUEPRINTS REGISTRADOS

| # | Blueprint | URL Prefix | Estado |
|---|-----------|------------|--------|
| 1 | `auth_bp` | `/auth` | ✅ Correcto |
| 2 | `dash_bp` | `/` | ✅ Correcto |
| 3 | `docs_bp` | `/documentos` | ✅ Correcto |
| 4 | `pqrs_bp` | `/pqrs` | ⚠️ Debe ajustarse |
| 5 | `gis_bp` | `/gis` | ⚠️ Debe ajustarse |
| 6 | `bh_bp` | `/balance` | ✅ Correcto |
| 7 | `com_bp` | `/comunicaciones` | ✅ Correcto |
| 8 | **`proy_bp`** | `/proyectos` | 🔴 **Debe eliminarse** |
| 9 | `api_bp` | `/api` | ✅ Correcto |
| 10 | `fin_bp` | `/finanzas` | ✅ Correcto |
| 11 | `rep_bp` | `/reportes-normativos` | ✅ Correcto |
| 12 | `aud_bp` | `/auditoria` | ✅ Correcto |
| 13 | `proy2_bp` | `/proyectos2` | ✅ Correcto (GA-08) |
| 14 | **`em_bp`** | `/emergencias` | 🔴 **Debe unificarse** |
| 15 | `conv_bp` | `/convenios` | ✅ Correcto (GF-04) |
| 16 | **`carpetas_bp`** | `/carpetas` | 🟡 Debe ajustarse |
| 17 | **`expedientes_bp`** | `/expedientes` | 🟡 Debe ajustarse |
| 18 | `cal_bp` | `/calidad-agua` | ✅ Correcto (GA-02) |
| 19 | `inv_bp` | `/inventarios` | ✅ Correcto (GF-05) |
| 20 | `sus_bp` | `/suscriptores` | ✅ Correcto (GC-01) |
| 21 | `ot_bp` | `/ordenes-trabajo` | ✅ Correcto (GA-07) |
| 22 | `lab_bp` | `/laboral` | ✅ Correcto (GL-01) |

**Hallazgo crítico:** `proy_bp` y `proy2_bp` coexisten en `app.py`. El Blueprint `proyectos` (v1) sigue registrado activo junto a `proyectos_v2` (GA-08). Hay dos sistemas de proyectos corriendo simultáneamente. `proy_bp` debe ser descomisionado.

**Hallazgo crítico:** `em_bp` (emergencias) no tiene asignación institucional dentro de la estructura GE/GC/GF/GA/GL aprobada. Debe unificarse con GA-07 (Órdenes de Trabajo) o GA-08 (Proyectos).

**Hallazgo medio:** `carpetas_bp` y `expedientes_bp` no tienen asignación institucional clara. Podrían formar parte de la gestión documental (GE área o Documentos), pero no están referenciados en la arquitectura aprobada.

---

### 1.2 BASE DE DATOS — MIGRACIONES

| Migración | Nombre | Tablas Creadas | Estado |
|-----------|--------|----------------|--------|
| 016 | `agregar_moneda_bancos` | ALTER bancos | ✅ Correcto |
| 017 | `pqrs_sspd_campos` | ALTER pqrs | ✅ Correcto |
| 018 | `pqrs_causales_sspd` | `pqrs_causales_sspd` | ⚠️ Debe ajustarse |
| 019 | `indices_rendimiento` | Índices | ✅ Correcto |
| 020 | `proyectos_periodo_flexible` | ALTER proyectos | ✅ Correcto |
| 021 | `tipos_proyecto_e_indices` | ALTER + índices | ✅ Correcto |
| 022 | `rc6_areas_estructura` | Tablas de áreas | ✅ Correcto |
| 023 | `calidad_agua_estructurada` | `calidad_parametros`, `calidad_muestras`, `calidad_resultados`, `calidad_puntos_muestreo` | ✅ Correcto |
| 024 | `balance_hidrico_mensual` | `balance_hidrico`, `lecturas_macromedidor`, `niveles_quebrada` | ⚠️ Debe ajustarse |
| 025 | `plan_cuentas_financiero` | `fin_plan_cuentas`, `fin_transacciones`, `fin_presupuesto` | ✅ Correcto |
| 026 | `suscriptores_gc01` | `gc_suscriptores`, `gc_conexiones`, `gc_pqrs_causales` | ✅ Correcto |
| 027 | `ordenes_trabajo_rc6` | `ga_ot_materiales`, `ga_ot_imagenes`, ALTER ordenes_trabajo | ✅ Correcto |
| 028 | `puntos_concertacion` | `ga_puntos_concertacion`, `ga_nivel_quebrada` | ⚠️ Debe ajustarse |
| 029 | `personal_gl01` | `gl_personal`, `gf_comprobantes`, `gf_consecutivos_comp` | ✅ Correcto |
| 030 | `gobierno_ge01` | `ge_actas`, `ge_resoluciones` | 🔴 **Debe ajustarse** |
| 031 | `pqrs_jerarquia` | `gc_servicios`, `gc_tipo_solicitante`, `gc_medios_recepcion`, ALTER gc_pqrs_causales | ✅ Correcto |

**Hallazgo (018):** Tabla `pqrs_causales_sspd` coexiste con `gc_pqrs_causales` (migración 026). Hay dos tablas de causales PQRS en paralelo: una normativa SSPD (estática) y una interna parametrizable. El sistema de rutas usa ambas. Debe unificarse el modelo.

**Hallazgo (024):** La tabla `niveles_quebrada` almacena `nivel_cm` como campo libre (INTEGER) sin restricción de intervalo. La arquitectura aprobada exige intervalos de 20 cm en 20 cm. No existe CHECK CONSTRAINT ni validación en backend que fuerce este intervalo.

**Hallazgo (028):** Existe `ga_nivel_quebrada` (migración 028) Y `niveles_quebrada` (migración 024) — dos tablas con la misma responsabilidad funcional. Duplicación de entidad.

**Hallazgo (030):** Las tablas `ge_actas` y `ge_resoluciones` existen en la base de datos pero **no tienen blueprint, rutas ni templates asociados**. Son tablas huérfanas inaccesibles desde la interfaz.

---

### 1.3 MENÚ SIDEBAR — NAVEGACIÓN

| Ítem del Menú | Endpoint Apuntado | Estado |
|---------------|-------------------|--------|
| Panel | `dashboard.index` | ✅ Correcto |
| Documentos › Todos | `documentos.listar` | ✅ Correcto |
| Documentos › Nuevo | `documentos.nuevo` | ✅ Correcto |
| GC-01 Suscriptores | `suscriptores.panel` | ✅ Correcto |
| GC-02 PQRS | `pqrs.listar` | ✅ Correcto |
| Comunicaciones | `comunicaciones.listar` | ⚠️ Sin clasificación GC |
| GF-02 Comprobantes | `finanzas.comprobantes` | ✅ Correcto |
| GF-06 Caja Menor | `finanzas.caja` | ✅ Correcto |
| Cuentas Bancarias | `finanzas.bancos` | ⚠️ Falta código GF |
| Movimientos | `finanzas.movimientos` | ⚠️ Falta código GF |
| GF-05 Inventarios | `inventarios.panel` | ✅ Correcto |
| Contratos | `convenios.panel` | ⚠️ Falta código GF-04 |
| Plan de Cuentas | `finanzas.plan_cuentas` | ⚠️ Falta código GF |
| GA-01 Operación Acueducto | `gis.mapa` | 🔴 **Debe ajustarse** |
| GA-02 Calidad del Agua | `calidad_agua.panel` | ✅ Correcto |
| GA-03 Balance Hídrico | `balance_hidrico.panel` | ✅ Correcto |
| GA-07 Órdenes de Trabajo | `ordenes_trabajo.panel` | ✅ Correcto |
| GA-08 Proyectos | `/proyectos2/` | ✅ Correcto |
| GL-01 Personal | `laboral.panel` | ✅ Correcto |
| Reportes CAR/SSPD | `reportes_normativos.panel` | ✅ Correcto |
| Admin › Diagnóstico | `auditoria.diagnosticos` | ✅ Correcto |

**Hallazgo crítico:** GA-01 "Operación Acueducto" apunta directamente a `gis.mapa`. El mapa GIS es una herramienta transversal, no el panel de GA-01. GA-01 debe ser un panel operativo propio (estado de redes, activos, infraestructura, operación en tiempo real) que consuma GIS como fuente de datos.

**Hallazgo medio:** GE (Gobierno Empresarial) no aparece en ningún ítem del menú. Las tablas `ge_actas` y `ge_resoluciones` son inaccesibles.

**Hallazgo medio:** Comunicaciones no tiene clasificación institucional en el menú. No está asignada explícitamente a GC.

---

### 1.4 MÓDULOS POR ÁREA INSTITUCIONAL

#### ÁREA GE — GOBIERNO EMPRESARIAL

| Módulo | Código | Blueprint | Rutas | Template | Tablas BD | Estado |
|--------|--------|-----------|-------|----------|-----------|--------|
| Actas y Resoluciones | GE-01 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ✅ `ge_actas`, `ge_resoluciones` | 🔴 **Debe implementarse** |
| Junta Directiva | GE-02 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ❌ Ausente | 🔴 No implementado |
| Estatutos | GE-03 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ❌ Ausente | 🔴 No implementado |
| Resoluciones | GE-04 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ❌ Ausente | 🔴 No implementado |
| Revisión Fiscal | GE-05 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ❌ Ausente | 🔴 No implementado |

**VEREDICTO GE:** Área sin implementación funcional. Solo existen dos tablas huérfanas. **Brecha crítica.**

---

#### ÁREA GC — GESTIÓN COMERCIAL

| Módulo | Código | Blueprint | Rutas | Template | Tablas BD | Estado |
|--------|--------|-----------|-------|----------|-----------|--------|
| Suscriptores | GC-01 | ✅ `sus_bp` | ✅ 9 endpoints | ✅ Completo | ✅ `gc_suscriptores`, `gc_conexiones` | ✅ Correcto |
| PQRS | GC-02 | ✅ `pqrs_bp` | ✅ Múltiples | ✅ 4 templates | ✅ Con jerarquía 4 niveles | ⚠️ Debe ajustarse |
| Facturación | GC-03 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ❌ Ausente | — (excluido por diseño) |
| Contratos de Servicio | GC-04 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ❌ Ausente | 🔴 No implementado |
| Cartera | GC-05 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ❌ Ausente | 🔴 No implementado |

**Nota GC-03:** Facturación fue excluida por decisión arquitectónica aprobada. SIGCA no es software de facturación. ESTADO: Correcto por diseño.

**Hallazgo GC-02:** El formulario `pqrs/nueva.html` implementa DOS sistemas de clasificación simultáneos: (a) Jerarquía nueva aprobada RC6 (`gc_servicios` → `gc_tipo_solicitante` → `gc_medios_recepcion` → `gc_pqrs_causales`) y (b) Sistema normativo SSPD antiguo (`grupo_causal` → `causal_codigo` → `subcausal`). El campo `fk_causal_id` del nuevo sistema no está conectado al modelo de datos de `pqrs` — solo se renderiza en el formulario pero no se guarda en la tabla `pqrs`.

---

#### ÁREA GF — GESTIÓN FINANCIERA

| Módulo | Código | Blueprint | Rutas | Template | Tablas BD | Estado |
|--------|--------|-----------|-------|----------|-----------|--------|
| Presupuesto | GF-01 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ✅ `fin_presupuesto` | ⚠️ Tabla sin frontend |
| Comprobantes | GF-02 | ✅ `fin_bp` | ✅ 4 endpoints | ✅ Completo | ✅ `gf_comprobantes` | ✅ Correcto |
| Cuentas Bancarias + Movimientos | GF-02b | ✅ `fin_bp` | ✅ Múltiples | ✅ 2 templates | ✅ `bancos`, `movimientos_financieros` | ✅ Correcto |
| Plan de Cuentas + Transacciones | GF-03 | ✅ `fin_bp` | ✅ 6 endpoints | ✅ 2 templates | ✅ `fin_plan_cuentas`, `fin_transacciones` | ✅ Correcto |
| Contratos / Convenios | GF-04 | ✅ `conv_bp` | ✅ Múltiples | ✅ 2 templates | ✅ (convenios) | ✅ Correcto |
| Inventarios | GF-05 | ✅ `inv_bp` | ✅ Múltiples | ✅ Completo | ✅ `inventario_items` | ✅ Correcto |
| Caja Menor | GF-06 | ✅ `fin_bp` | ✅ 5 endpoints | ✅ Completo | ✅ `caja_chica` | ✅ Correcto |

**Hallazgo GF-01:** La tabla `fin_presupuesto` fue creada en la migración 025 pero no tiene blueprint, rutas ni template asociados. Es una tabla huérfana.

**VEREDICTO GF:** Área con mejor cobertura del sistema. GF-02 a GF-06 operativos. Brecha en GF-01 (Presupuesto sin frontend).

---

#### ÁREA GA — GESTIÓN AMBIENTAL Y OPERATIVA

| Módulo | Código | Blueprint | Rutas | Template | Tablas BD | Estado |
|--------|--------|-----------|-------|----------|-----------|--------|
| Operación Acueducto | GA-01 | ⚠️ Mapeado a GIS | ⚠️ Sin panel propio | ❌ Ausente | ❌ Sin tablas operativas | 🔴 **Debe ajustarse** |
| Calidad del Agua | GA-02 | ✅ `cal_bp` | ✅ 9 endpoints | ✅ Completo | ✅ 4 tablas Res. 2115 | ✅ Correcto |
| Balance Hídrico | GA-03 | ✅ `bh_bp` | ✅ 8 endpoints | ✅ Completo | ✅ `balance_hidrico`, `lecturas_macromedidor`, `niveles_quebrada` | ⚠️ Debe ajustarse |
| Infraestructura | GA-04 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ❌ Ausente | 🔴 No implementado |
| Mantenimiento | GA-05 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ❌ Ausente | 🔴 No implementado |
| Cuenca | GA-06 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ❌ Ausente | 🔴 No implementado |
| Órdenes de Trabajo | GA-07 | ✅ `ot_bp` | ✅ 7 endpoints | ✅ Completo | ✅ OT + materiales + imágenes | ✅ Correcto |
| Proyectos | GA-08 | ✅ `proy2_bp` | ✅ Múltiples | ✅ Completo | ✅ Tipos: PUEAA/PSMV/PEC/Obras | ✅ Correcto |

**Hallazgo GA-01:** No existe un panel de Operación Acueducto. El menú apunta a `gis.mapa` como sustituto. GIS es herramienta transversal. GA-01 debe mostrar estado de redes, activos en operación, alertas de presión, disponibilidad del sistema.

**Hallazgo GA-03:** La tabla `niveles_quebrada` acepta cualquier valor entero en `nivel_cm`. La arquitectura aprobada establece lectura cada 20 cm (0, 20, 40, 60, ...). No existe validación a nivel de BD ni de API que fuerce este escalonamiento. Además coexisten dos tablas: `niveles_quebrada` (migración 024) y `ga_nivel_quebrada` (migración 028) con la misma responsabilidad.

**Verificación PUEAA/PSMV/PEC:**
- En `proyectos_v2.py` el CSS tiene clases `.tipo-pueaa` y `.tipo-psmv`.
- El panel header original decía "PUEAA · PSMV · Obras" (ya corregido a "GA-08 — Gestión de Proyectos").
- `proy_bp` (v1 legacy) aún está registrado en `app.py` — puede crear confusión y rutas duplicadas.
- **VEREDICTO:** PUEAA/PSMV/PEC están correctamente integrados como tipos de proyecto en GA-08. El riesgo es la coexistencia de `proy_bp` (v1).

---

#### ÁREA GL — GESTIÓN LABORAL

| Módulo | Código | Blueprint | Rutas | Template | Tablas BD | Estado |
|--------|--------|-----------|-------|----------|-----------|--------|
| Personal | GL-01 | ✅ `lab_bp` | ✅ 4 endpoints | ✅ Completo | ✅ `gl_personal` | ✅ Correcto |
| Nómina | GL-02 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ❌ Ausente | 🔴 No implementado |
| Vacaciones / Licencias | GL-03 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ❌ Ausente | 🔴 No implementado |
| Sanciones Disciplinarias | GL-04 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ❌ Ausente | 🔴 No implementado |
| Formación / Capacitación | GL-05 | ❌ Ausente | ❌ Ausente | ❌ Ausente | ❌ Ausente | 🔴 No implementado |

**VEREDICTO GL:** Solo GL-01 Personal implementado. GL-02 a GL-05 no existen.

---

### 1.5 FORMULARIOS

| Formulario | Módulo | Estado | Observación |
|------------|--------|--------|-------------|
| `pqrs/nueva.html` | GC-02 | ⚠️ Debe ajustarse | Dos sistemas de causales en paralelo. `fk_causal_id` no se persiste en tabla `pqrs`. |
| `suscriptores/panel.html` | GC-01 | ✅ Correcto | Modal funcional con todos los campos requeridos. |
| `ordenes_trabajo/panel.html` | GA-07 | ✅ Correcto | Ciclo de vida completo CREADA→CERRADA. |
| `laboral/panel.html` | GL-01 | ✅ Correcto | Modal contratación con tipo, salario, EPS. |
| `finanzas/comprobantes.html` | GF-02 | ✅ Correcto | Ingreso/Egreso diferenciados. Numeración consecutiva. |
| `calidad_agua/panel.html` | GA-02 | ✅ Correcto | `toggleNoAcept()` habilita `valor_encontrado` cuando NO_ACEPTABLE. |
| `balance/panel.html` | GA-03 | ✅ Correcto | Macromedidor mensual. IANC calculado. |

---

### 1.6 ENDPOINTS

| Área | Endpoints totales auditados | Correctos | Deben ajustarse | Deben eliminarse |
|------|----------------------------|-----------|-----------------|------------------|
| GC | 12 | 10 | 2 | 0 |
| GF | 21 | 21 | 0 | 0 |
| GA | 24 | 22 | 2 | 0 |
| GL | 4 | 4 | 0 | 0 |
| GE | 0 | 0 | 0 | 0 |
| Proyectos v1 | 8 (estimado) | 0 | 0 | 8 |

**Endpoints a eliminar (proyectos v1):** Todos los endpoints de `proy_bp` deben ser removidos o redireccionados a `proy2_bp`. Mantenerlos activos genera rutas duplicadas y confusión en la navegación.

---

### 1.7 GIS

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Blueprint registrado | ✅ Correcto | `gis_bp` en `/gis` |
| Conversión WGS84/UTM | ✅ Correcto | Soporta coordenadas lat/lon y UTM |
| GeoJSON features | ✅ Correcto | `row_to_geojson_feature()` convierte filas de BD |
| Alimenta GA-01 | 🔴 **Ausente** | No existe integración activa con panel GA-01 |
| Alimenta GA-04 Infraestructura | 🔴 **Ausente** | GA-04 no existe |
| Alimenta GA-07 OT | ⚠️ Parcial | `fk_punto_gis_id` en ordenes_trabajo (migración 027) pero sin UI de mapa en OT |
| Puntos de concertación | ⚠️ Parcial | Tabla `ga_puntos_concertacion` existe, sin frontend |

**VEREDICTO GIS:** GIS existe como mapa Leaflet funcional pero opera de forma aislada. La arquitectura aprobada define GIS como **fuente maestra** que alimenta GA-01, GA-04, GA-05, GA-06 y GA-07. Esta integración bidireccional no está implementada.

---

### 1.8 PROYECTOS (GA-08)

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| PEC como tipo de proyecto | ✅ Correcto | CSS `.tipo-otro` puede usarlo; `tipo_proyecto` es campo libre |
| PUEAA como tipo de proyecto | ✅ Correcto | CSS `.tipo-pueaa` definido |
| PSMV como tipo de proyecto | ✅ Correcto | CSS `.tipo-psmv` definido |
| Módulo independiente PUEAA | ✅ Correcto | NO existe como módulo independiente |
| Módulo independiente PSMV | ✅ Correcto | NO existe como módulo independiente |
| Módulo independiente PEC | ✅ Correcto | NO existe como módulo independiente |
| proyectos v1 (proy_bp) aún activo | 🔴 **Debe eliminarse** | Registrado en app.py línea 38 |
| Templates legacy proyectos/ | 🟡 Debe ajustarse | Carpeta `templates/proyectos/` con 4 archivos legacy |

---

### 1.9 PQRS — VERIFICACIÓN JERARQUÍA 4 NIVELES

| Nivel | Componente | BD | Backend API | Frontend | Estado |
|-------|-----------|----|----|---------|--------|
| Nivel 1 — Servicio | `gc_servicios` | ✅ Migración 031 | ✅ `/pqrs/api/gc-servicios` | ✅ Radio buttons en `nueva.html` | ✅ Correcto |
| Nivel 2 — Solicitante | `gc_tipo_solicitante` | ✅ Migración 031 | ❌ Sin endpoint dedicado | ✅ Radio buttons ya existentes | ⚠️ Debe ajustarse |
| Nivel 3 — Medio | `gc_medios_recepcion` | ✅ Migración 031 | ✅ `/pqrs/api/gc-medios` | ✅ Select en `nueva.html` | ✅ Correcto |
| Nivel 4 — Causal | `gc_pqrs_causales` + `fk_servicio_id` | ✅ Migración 031 | ✅ `/pqrs/api/gc-causales` | ✅ Select cascada en `nueva.html` | ⚠️ Debe ajustarse |

**Hallazgo crítico:** El campo `fk_causal_id` (nueva jerarquía) se renderiza en el formulario pero **no existe en el modelo de datos de la tabla `pqrs`** ni en el handler POST de `pqrs_bp`. Los datos del Nivel 4 (causal interna) se pierden al radicar. El modelo de la tabla `pqrs` conserva `causal_codigo` (SSPD) pero no tiene columna para la nueva causal paramétrica.

**Hallazgo:** El Nivel 2 (tipo solicitante) tiene tabla en BD (`gc_tipo_solicitante`) pero no tiene endpoint API propio. El formulario usa radio buttons HTML estáticos que no se conectan a la tabla dinámica.

---

### 1.10 CALIDAD DEL AGUA — VERIFICACIÓN RES. 2115/2007

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Referencia normativa Res. 2115/2007 | ✅ Correcto | Documentada en `routes/calidad_agua.py` |
| Estado ACEPTABLE | ✅ Correcto | Opción en `param-res` select |
| Estado NO_ACEPTABLE | ✅ Correcto | Opción con `toggleNoAcept()` |
| Estado NO_MEDIDO | ✅ Correcto | Tercera opción disponible |
| Campo `valor_encontrado` condicional | ✅ Correcto | `display:none` por defecto; se activa con NO_ACEPTABLE |
| Modal de resultados (no alert) | ✅ Correcto | Mejorado en RC6 — usa Bootstrap modal |
| Parámetros parametrizables | ✅ Correcto | `calidad_parametros` con activo flag y orden |
| Puntos de muestreo | ✅ Correcto | `calidad_puntos_muestreo` con coordenadas |
| Acciones correctivas | ✅ Correcto | Campo `accion_correctiva` en `calidad_resultados` |

**VEREDICTO GA-02:** Módulo correcto y completo según arquitectura aprobada.

---

### 1.11 BALANCE HÍDRICO — VERIFICACIÓN

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Macromedidor mensual | ✅ Correcto | `lecturas_macromedidor` y `balance_hidrico` (mes/año) |
| Nivel de quebrada | ⚠️ Debe ajustarse | Tabla existe pero sin validación de intervalos de 20 cm |
| IANC calculado | ✅ Correcto | Formula: `(produccion - facturado) / produccion * 100` |
| IPUF calculado | ✅ Correcto | `facturado_m3 / suscriptores` |
| IMA calculado | ✅ Correcto | Pérdidas por km de red |
| Exportación Excel | ✅ Correcto | Formato con openpyxl |
| Indicadores anuales | ✅ Correcto | `/api/indicadores/<anio>` |
| Duplicación de tablas nivel quebrada | 🔴 **Debe ajustarse** | `niveles_quebrada` (mig. 024) Y `ga_nivel_quebrada` (mig. 028) |

---

### 1.12 INVENTARIOS (GF-05)

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Blueprint registrado | ✅ Correcto | `inv_bp` en `/inventarios` |
| Template | ✅ Correcto | `templates/inventarios/panel.html` |
| Tabla BD | ✅ Correcto | `inventario_items` |
| Categorías | ✅ Correcto | material, equipo, herramienta, químico, activo, EPP, otro |
| Integración GF-05 en menú | ✅ Correcto | Sidebar apunta correctamente |
| Vinculación con OT (materiales) | ⚠️ Parcial | `ga_ot_materiales` tiene `fk_item_id` pero sin validación contra inventario |

---

### 1.13 COMPROBANTES DE TESORERÍA (GF-02)

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Comprobante de Ingreso | ✅ Correcto | Tipo INGRESO, número `I{AÑO}-{SEQ}` |
| Comprobante de Egreso | ✅ Correcto | Tipo EGRESO, número `E{AÑO}-{SEQ}` |
| Numeración consecutiva por año | ✅ Correcto | `gf_consecutivos_comp` por (anio, tipo) |
| Estado BORRADOR → APROBADO | ✅ Correcto | Aprobación requiere rol admin/presidente/tesorera |
| KPI Ingresos/Egresos/Neto | ✅ Correcto | Calculado en API con SUM por tipo |
| Movimientos bancarios | ✅ Correcto | `movimientos_financieros` con balance automático |
| Caja menor | ✅ Correcto | `caja_chica` con saldo corriente |

---

## PARTE 2 — MATRIZ GAP

### Comparativo ACTUAL vs ARQUITECTURA OBJETIVO

| Área | Módulo | Código | Estado ACTUAL | Estado OBJETIVO | GAP |
|------|--------|--------|---------------|-----------------|-----|
| **GE** | Actas y Resoluciones | GE-01 | Tablas huérfanas | Panel + CRUD completo | 🔴 Crítico |
| **GE** | Junta Directiva | GE-02 | Inexistente | Panel + documentos | 🔴 Crítico |
| **GE** | Estatutos | GE-03 | Inexistente | Gestión documental | 🔴 Crítico |
| **GE** | Resoluciones | GE-04 | Tablas huérfanas | Panel + CRUD | 🔴 Crítico |
| **GE** | Revisión Fiscal | GE-05 | Inexistente | Gestión informes | 🔴 Crítico |
| **GC** | Suscriptores | GC-01 | ✅ Completo | Completo | ✅ Sin GAP |
| **GC** | PQRS 4 niveles | GC-02 | Parcial (4 niveles en BD, form mixto) | Form limpio, causal persiste | 🟡 Medio |
| **GC** | Cartera | GC-05 | Inexistente | Saldo, mora, acuerdos | 🔴 Alto |
| **GF** | Presupuesto | GF-01 | Tabla sin frontend | Panel presupuestal | 🟡 Medio |
| **GF** | Comprobantes | GF-02 | ✅ Completo | Completo | ✅ Sin GAP |
| **GF** | Plan Cuentas + Transacciones | GF-03 | ✅ Completo | Completo | ✅ Sin GAP |
| **GF** | Convenios / Contratos | GF-04 | ✅ Completo | Completo | ✅ Sin GAP |
| **GF** | Inventarios | GF-05 | ✅ Completo | Completo + vinculación OT | 🟢 Mínimo |
| **GF** | Caja + Bancos + Movimientos | GF-06 | ✅ Completo | Completo | ✅ Sin GAP |
| **GA** | Operación Acueducto (panel propio) | GA-01 | Ausente (apunta a GIS) | Panel operativo con GIS | 🔴 Alto |
| **GA** | Calidad del Agua | GA-02 | ✅ Completo (Res. 2115) | Completo | ✅ Sin GAP |
| **GA** | Balance Hídrico | GA-03 | Funcional, duplicación tablas | Consolidado, 20cm validado | 🟡 Medio |
| **GA** | Infraestructura | GA-04 | Inexistente | GIS + activos + estado | 🔴 Alto |
| **GA** | Mantenimiento | GA-05 | Inexistente | Planes + OT preventiva | 🔴 Alto |
| **GA** | Cuenca | GA-06 | Inexistente | Puntos cuenca + niveles | 🔴 Alto |
| **GA** | Órdenes de Trabajo | GA-07 | ✅ Completo | Completo + link inventario | 🟢 Mínimo |
| **GA** | Proyectos (PUEAA/PSMV/PEC) | GA-08 | ✅ Correcto (tipos en v2), proy_bp aún activo | Solo proy2_bp | 🟡 Medio |
| **GL** | Personal | GL-01 | ✅ Completo | Completo | ✅ Sin GAP |
| **GL** | Nómina | GL-02 | Inexistente | Liquidación, recibos | 🔴 Alto |
| **GL** | Vacaciones / Licencias | GL-03 | Inexistente | Registro, aprobación | 🔴 Alto |
| **GL** | Sanciones | GL-04 | Inexistente | Proceso disciplinario | 🟡 Medio |
| **GL** | Capacitación | GL-05 | Inexistente | Registro cursos | 🟡 Medio |
| **Transversal** | GIS como fuente maestra | — | Mapa aislado | Integrado a GA-01, GA-04–07 | 🔴 Alto |
| **Transversal** | proy_bp (v1) activo | — | Activo y registrado | Eliminado | 🔴 Crítico |
| **Transversal** | emergencias sin clasificación | — | Blueprint activo sin área | Unificado en GA-07 o GA-08 | 🟡 Medio |

**Resumen GAP:**
- ✅ Sin GAP: 9 módulos
- 🟢 GAP mínimo: 2 módulos
- 🟡 GAP medio: 7 módulos
- 🔴 GAP alto/crítico: 15 módulos

---

## PARTE 3 — RIESGOS

### R-01 — proyectos v1 coexiste con proyectos v2
**Severidad:** 🔴 CRÍTICO
**Descripción:** `proy_bp` (proyectos v1) está registrado en `app.py` simultáneamente con `proy2_bp`. Ambos sirven rutas relacionadas con proyectos. Si un usuario o proceso interno llama a `/proyectos/` en lugar de `/proyectos2/`, accede al sistema antiguo con esquema diferente. Los datos creados en v1 no son visibles en v2.
**Módulo afectado:** GA-08, app.py

### R-02 — fk_causal_id de PQRS no se persiste
**Severidad:** 🔴 CRÍTICO
**Descripción:** El formulario `pqrs/nueva.html` renderiza el selector de "Causal del servicio" (Nivel 4 de la jerarquía aprobada) pero el handler POST del blueprint `pqrs` no lee ni guarda `fk_causal_id`. La tabla `pqrs` no tiene esa columna. Los datos del nuevo sistema de causales se pierden en cada radicación.
**Módulo afectado:** GC-02 PQRS

### R-03 — GE sin ninguna funcionalidad accesible
**Severidad:** 🔴 CRÍTICO
**Descripción:** Toda el Área de Gobierno Empresarial (GE-01 a GE-05) carece de implementación. Las tablas `ge_actas` y `ge_resoluciones` existen en la BD pero son inaccesibles. No hay menú, rutas, ni templates. Las actas y resoluciones de la Junta Directiva no se pueden gestionar.
**Módulo afectado:** GE-01 a GE-05

### R-04 — Duplicación tablas nivel de quebrada
**Severidad:** 🔴 ALTO
**Descripción:** Existen dos tablas con la misma responsabilidad funcional: `niveles_quebrada` (migración 024) y `ga_nivel_quebrada` (migración 028). El balance hídrico usa `niveles_quebrada`, mientras que el balance aprobado en RC6 debería usar `ga_nivel_quebrada`. Los datos quedan fragmentados y las consultas pueden devolver resultados incompletos o inconsistentes.
**Módulo afectado:** GA-03, BD

### R-05 — Intervalos de 20 cm en nivel de quebrada no validados
**Severidad:** 🔴 ALTO
**Descripción:** La arquitectura aprobada establece que el nivel de quebrada se registra cada 20 cm (escala: 0, 20, 40, 60...). La tabla `ga_nivel_quebrada.nivel_cm` es INTEGER sin CHECK CONSTRAINT. El endpoint no valida el valor. Un operador puede ingresar valores arbitrarios (37 cm, 153 cm) generando datos inconsistentes con la metodología aprobada.
**Módulo afectado:** GA-03

### R-06 — GA-01 Operación Acueducto sin panel propio
**Severidad:** 🟠 ALTO
**Descripción:** El menú sidebar apunta a `gis.mapa` como sustituto de GA-01. GIS es una herramienta transversal. GA-01 debe mostrar estado operativo (presión de red, disponibilidad de fuentes, activos en operación, alertas). Sin este panel, los operadores no tienen un punto de control unificado del acueducto.
**Módulo afectado:** GA-01, Sidebar

### R-07 — GIS no integrado con módulos GA
**Severidad:** 🟠 ALTO
**Descripción:** GIS opera como mapa visualizador aislado. La arquitectura aprobada establece que GIS es la fuente maestra para GA-01 (activos), GA-04 (infraestructura), GA-05 (mantenimiento), GA-06 (cuenca) y GA-07 (OT georreferenciadas). El campo `fk_punto_gis_id` existe en `ordenes_trabajo` pero sin UI en el mapa para asignar o visualizar OT.
**Módulo afectado:** GIS, GA-01, GA-04, GA-05, GA-06, GA-07

### R-08 — emergencias blueprint sin clasificación institucional
**Severidad:** 🟡 MEDIO
**Descripción:** `em_bp` está registrado pero no pertenece a ninguna de las 5 áreas institucionales (GE/GC/GF/GA/GL). No aparece en el sidebar. Su funcionalidad debería integrarse en GA-07 (Órdenes de Trabajo de emergencia) o GA-08 (Proyectos de emergencia). Mantenerlo aislado genera deuda técnica.
**Módulo afectado:** em_bp, app.py

### R-09 — fin_presupuesto sin frontend
**Severidad:** 🟡 MEDIO
**Descripción:** La tabla `fin_presupuesto` fue creada en migración 025 con datos de presupuesto mensual por cuenta. No existe endpoint, template ni menú para gestionarla. Los datos de presupuesto ingresados durante la inicialización no son accesibles para el usuario. GF-01 queda funcional solo a nivel de BD.
**Módulo afectado:** GF-01

### R-10 — carpetas y expedientes sin área institucional asignada
**Severidad:** 🟡 MEDIO
**Descripción:** Los blueprints `carpetas_bp` y `expedientes_bp` están registrados y tienen templates pero no tienen asignación dentro de GE/GC/GF/GA/GL. No aparecen en el sidebar. Probablemente corresponden a la Gestión Documental, pero no están clasificados ni vinculados a la arquitectura aprobada.
**Módulo afectado:** carpetas_bp, expedientes_bp

### R-11 — pqrs_causales_sspd coexiste con gc_pqrs_causales
**Severidad:** 🟡 MEDIO
**Descripción:** Existen dos tablas de causales PQRS: `pqrs_causales_sspd` (modelo normativo SSPD estático) y `gc_pqrs_causales` (modelo interno parametrizable). El endpoint `/pqrs/api/causales` usa `pqrs_causales_sspd` si existe con datos; el endpoint `/pqrs/api/gc-causales` usa `gc_pqrs_causales`. Hay riesgo de que los usuarios vean dos catálogos de causales sin coherencia entre ellos.
**Módulo afectado:** GC-02, BD

### R-12 — GL-02 a GL-05 inexistentes
**Severidad:** 🟡 MEDIO
**Descripción:** Solo GL-01 (Personal) está implementado. Sin GL-02 (Nómina), GL-03 (Vacaciones), GL-04 (Sanciones) y GL-05 (Capacitación), la gestión laboral queda reducida a un directorio de empleados sin capacidades de gestión del talento humano.
**Módulo afectado:** GL

---

## PARTE 4 — RECOMENDACIONES

> **Nota:** Estas recomendaciones son de alto nivel arquitectónico. No incluyen pasos de implementación.

### REC-01 — Eliminar proyectos v1 (proy_bp)
**Prioridad:** INMEDIATA
Remover el registro de `proy_bp` en `app.py` y redirigir cualquier enlace residual a `proy2_bp`. Archivar o eliminar la carpeta `templates/proyectos/`. Una sola versión del motor de proyectos es crítico para la integridad de datos.

### REC-02 — Persistir fk_causal_id en modelo PQRS
**Prioridad:** INMEDIATA
Agregar la columna `fk_causal_id` a la tabla `pqrs` y actualizar el handler POST para capturar y almacenar el dato. El formulario ya captura el valor; falta el almacenamiento. Esto completa el ciclo de la jerarquía 4 niveles aprobada.

### REC-03 — Consolidar tablas nivel de quebrada
**Prioridad:** ALTA
Unificar `niveles_quebrada` (migración 024) y `ga_nivel_quebrada` (migración 028) en una sola tabla. Decidir cuál conservar (se recomienda `ga_nivel_quebrada` por pertenecer al diseño RC6). Migrar datos si los hubiere.

### REC-04 — Implementar GE-01 Actas y Resoluciones
**Prioridad:** ALTA
Las tablas `ge_actas` y `ge_resoluciones` ya existen. Se requiere blueprint, rutas CRUD y template. GE-01 es el primer módulo del área de Gobierno Empresarial y es exigencia regulatoria para acueductos comunitarios colombianos (rendición de cuentas a Junta Directiva).

### REC-05 — Crear GA-01 Operación Acueducto como panel propio
**Prioridad:** ALTA
Diseñar un panel GA-01 que muestre: estado de fuentes de captación, estado de la PTAP, presión de distribución, activos críticos, alertas activas. GIS debe alimentar este panel como fuente de datos geoespaciales, no ser el panel en sí mismo.

### REC-06 — Validar intervalo 20 cm en nivel de quebrada
**Prioridad:** ALTA
Agregar validación en el endpoint de registro de nivel de quebrada para que solo acepte valores múltiplos de 20 (nivel_cm % 20 == 0). Opcionalmente agregar CHECK CONSTRAINT en la migración correspondiente.

### REC-07 — Integrar GIS con GA-07 Órdenes de Trabajo
**Prioridad:** MEDIA
Habilitar en el panel GA-07 la capacidad de ver OT georreferenciadas en el mapa y asignar `fk_punto_gis_id` desde el mapa. El campo ya existe en la tabla; falta la interfaz.

### REC-08 — Unificar emergencias en GA-07 o GA-08
**Prioridad:** MEDIA
Reclasificar el contenido de `em_bp` dentro de la estructura GA. Si son fallas/incidentes urgentes → GA-07 con prioridad URGENTE. Si son proyectos de emergencia → GA-08. Eliminar `em_bp` como blueprint independiente.

### REC-09 — Implementar GA-04 Infraestructura
**Prioridad:** MEDIA
GA-04 es crítico para la gestión de activos físicos del acueducto (tuberías, válvulas, tanques, bocatomas). GIS debe ser la fuente maestra. Los activos registrados en GIS deben ser accesibles y editables desde GA-04.

### REC-10 — Asignar carpetas y expedientes a Gestión Documental
**Prioridad:** BAJA
Los blueprints `carpetas_bp` y `expedientes_bp` deben ser clasificados dentro de la arquitectura documental (probablemente como sub-módulos de la sección Documentos). Agregar accesos en el sidebar bajo Gestión Documental.

---

## RESUMEN EJECUTIVO

| Indicador | Valor |
|-----------|-------|
| Blueprints auditados | 22 |
| Blueprints correctos | 17 |
| Blueprints a eliminar | 1 (`proy_bp`) |
| Blueprints a unificar | 2 (`em_bp`, `carpetas_bp`) |
| Migraciones auditadas | 16 (016–031) |
| Migraciones con hallazgos | 4 (018, 024, 028, 030) |
| Módulos sin GAP | 9 |
| Módulos con GAP crítico | 5 |
| Módulos con GAP alto | 7 |
| Módulos con GAP medio | 7 |
| Riesgos identificados | 12 |
| Riesgos críticos | 3 |
| Riesgos altos | 4 |
| Riesgos medios | 5 |
| Recomendaciones | 10 |
| Recomendaciones inmediatas | 2 |
| Recomendaciones altas | 4 |
| Recomendaciones medias | 3 |
| Recomendaciones bajas | 1 |

**Porcentaje de cobertura arquitectónica actual:** ~42% (9 de 21 módulos sin GAP significativo)
**Módulos más críticos sin implementar:** GE-01 a GE-05 (Gobierno), GA-01, GA-04, GA-05, GA-06

---

*Auditoría RC6.1 — PARAGUASMJ — 2026-06-13*
*Generada sobre rama: claude/blissful-franklin-p9g7U — commit 5e0e7be*
