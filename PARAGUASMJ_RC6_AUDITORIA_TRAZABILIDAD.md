# PARAGUASMJ — AUDITORÍA RC6 · INFORME TÉCNICO DE TRAZABILIDAD
**Fecha:** 2026-06-13  
**Tipo:** Auditoría de Verificación — Sin modificaciones de código  
**Alcance:** 12 puntos de verificación RC6 + Matriz de Trazabilidad Completa

---

## RESUMEN EJECUTIVO

| Área | Estado |
|---|---|
| Migraciones 026-031 en disco | ✅ PASA |
| Migraciones registradas en app.py | ✅ PASA |
| Blueprints RC6 (sus/ot/lab) registrados | ✅ PASA |
| Rutas huérfanas | ⚠️ ALERTA — proy_bp v1 activo junto a proy2_bp |
| Navegación en templates (sidebar) | ✅ PASA |
| Modelos vs arquitectura RC6 | ⚠️ ALERTA — tabla duplicada nivel quebrada |
| Referencias prohibidas: Facturación | ❌ FALLA CRÍTICA — pqrs.py activo |
| Referencias prohibidas: Presión | ❌ FALLA CRÍTICA — pqrs.py activo |
| Referencias prohibidas: Calidad agua antigua | ✅ PASA |
| Referencias PQRS SSPD 01-99 | ❌ FALLA CRÍTICA — diccionarios activos |
| GE/GC/GF/GA/GL únicas áreas maestras | ⚠️ ALERTA — PEC independiente |
| Proyectos genéricos (PUEAA/PSMV/PEC como instancias) | ⚠️ ALERTA — em_bp viola arquitectura |

**Hallazgos críticos: 3 · Alertas: 4 · Aprobados: 5**

---

## PUNTO 1 — MIGRACIONES 026-031 EN DISCO

**Estado: ✅ PASA**

| Archivo | Existencia |
|---|---|
| `database/migrations/026_suscriptores_gc01.py` | ✅ Presente |
| `database/migrations/027_ordenes_trabajo_rc6.py` | ✅ Presente |
| `database/migrations/028_puntos_concertacion.py` | ✅ Presente |
| `database/migrations/029_personal_gl01.py` | ✅ Presente |
| `database/migrations/030_gobierno_ge01.py` | ✅ Presente |
| `database/migrations/031_pqrs_jerarquia.py` | ✅ Presente |

---

## PUNTO 2 — MIGRACIONES REGISTRADAS EN app.py

**Estado: ✅ PASA**

Función `_run_migrations()` en `app.py` líneas 267-272:

```
"database.migrations.026_suscriptores_gc01"
"database.migrations.027_ordenes_trabajo_rc6"
"database.migrations.028_puntos_concertacion"
"database.migrations.029_personal_gl01"
"database.migrations.030_gobierno_ge01"
"database.migrations.031_pqrs_jerarquia"
```

Todas registradas en orden. Sistema idempotente verificado.

---

## PUNTO 3 — BLUEPRINTS RC6 REGISTRADOS EN app.py

**Estado: ✅ PASA (con advertencia)**

| Blueprint | Import (línea) | Register (línea) | URL |
|---|---|---|---|
| `sus_bp` | 46 | 69 | `/suscriptores` |
| `ot_bp` | 47 | 70 | `/ordenes-trabajo` |
| `lab_bp` | 48 | 71 | `/laboral` |

**⚠️ Advertencia coexistente:**  
`proy_bp` (v1) importado en línea 34 y registrado en línea 57 en `/proyectos`.  
`proy2_bp` (v2) importado en línea 39 y registrado en línea 62 en `/proyectos2`.  
Dos versiones del mismo módulo activas simultáneamente — riesgo de conflicto.

---

## PUNTO 4 — RUTAS HUÉRFANAS

**Estado: ⚠️ ALERTA**

| Ruta | Blueprint | Problema |
|---|---|---|
| `/proyectos/*` | `proy_bp` (v1) | Versión obsoleta activa — debería estar eliminada |
| `/emergencias/*` | `em_bp` | PEC como módulo independiente viola arquitectura RC6 |

`proy_bp` v1 no tiene sidebar entry en `base.html`, por lo que sus rutas son funcionales pero invisibles — rutas fantasma accesibles directamente por URL.

---

## PUNTO 5 — NAVEGACIÓN EN TEMPLATES (SIDEBAR)

**Estado: ✅ PASA**

Verificados los 26 `url_for()` en `templates/base.html`. Todos los destinos existen en sus respectivos blueprints:

| url_for | Blueprint | Función | Estado |
|---|---|---|---|
| `dashboard.index` | `dash_bp` | `index` | ✅ |
| `documentos.listar` | `docs_bp` | `listar` | ✅ |
| `documentos.nuevo` | `docs_bp` | `nuevo` | ✅ |
| `suscriptores.panel` | `sus_bp` | `panel` | ✅ |
| `pqrs.listar` | `pqrs_bp` | `listar` | ✅ |
| `comunicaciones.listar` | `com_bp` | `listar` | ✅ |
| `finanzas.comprobantes` | `fin_bp` | `comprobantes` | ✅ |
| `finanzas.caja` | `fin_bp` | `caja` | ✅ |
| `finanzas.bancos` | `fin_bp` | `bancos` | ✅ |
| `finanzas.movimientos` | `fin_bp` | `movimientos` | ✅ |
| `inventarios.panel` | `inv_bp` | `panel` | ✅ |
| `convenios.panel` | `conv_bp` | `panel` | ✅ |
| `finanzas.plan_cuentas` | `fin_bp` | `plan_cuentas` | ✅ |
| `gis.mapa` | `gis_bp` | `mapa` | ✅ |
| `calidad_agua.panel` | `cal_bp` | `panel` | ✅ |
| `balance_hidrico.panel` | `bh_bp` | `panel` | ✅ |
| `ordenes_trabajo.panel` | `ot_bp` | `panel` | ✅ |
| `laboral.panel` | `lab_bp` | `panel` | ✅ |
| `reportes_normativos.panel` | `rep_bp` | `panel` | ✅ |
| `auditoria.usuarios` | `aud_bp` | `usuarios` | ✅ |
| `auditoria.panel` | `aud_bp` | `panel` | ✅ |
| `configuracion` | `app.py` | `configuracion` | ✅ |
| `auditoria.diagnosticos` | `aud_bp` | `diagnosticos` | ✅ |
| `autenticacion.perfil` | `auth_bp` | `perfil` | ✅ |
| `autenticacion.logout` | `auth_bp` | `logout` | ✅ |

Sección GA en sidebar: `/proyectos2/` hardcoded (no usa `url_for`) — funcional pero no sigue el patrón del resto del sidebar.

---

## PUNTO 6 — MODELOS vs ARQUITECTURA RC6

**Estado: ⚠️ ALERTA**

| Tabla | Migración | Área | Observación |
|---|---|---|---|
| `gc_suscriptores` | 026 | GC | ✅ Correcto |
| `gc_contratos_servicio` | 026 | GC | ✅ Correcto |
| `gc_lecturas_consumo` | 026 | GC | ✅ Correcto |
| `ga_ordenes_trabajo` | 027 | GA | ✅ Correcto |
| `ga_ot_materiales` | 027 | GA | ✅ Correcto |
| `ga_puntos_concertacion` | 028 | GA | ✅ Correcto |
| `niveles_quebrada` | 024 | GA | ⚠️ Nombre sin prefijo `ga_` |
| `ga_nivel_quebrada` | 028 | GA | ⚠️ **DUPLICADA** con `niveles_quebrada` — misma entidad, dos tablas |
| `gl_empleados` | 029 | GL | ✅ Correcto |
| `gl_contratos_labor` | 029 | GL | ✅ Correcto |
| `ge_actas` | 030 | GE | ✅ Correcto — sin frontend activo |
| `ge_resoluciones` | 030 | GE | ✅ Correcto — sin frontend activo |
| `gc_servicios` | 031 | GC | ✅ Correcto |
| `gc_tipo_solicitante` | 031 | GC | ✅ Correcto |
| `gc_medios_recepcion` | 031 | GC | ✅ Correcto |
| `riesgos_pec` | emergencias | — | ❌ Sin prefijo de área, fuera de GA |

**Duplicado crítico:** `niveles_quebrada` (mig024) y `ga_nivel_quebrada` (mig028) representan la misma entidad. El código de balance hídrico debe apuntar a una sola.

---

## PUNTO 7 — REFERENCIAS PROHIBIDAS: FACTURACIÓN

**Estado: ❌ FALLA CRÍTICA**

| Archivo | Línea | Contenido | Tipo |
|---|---|---|---|
| `routes/pqrs.py` | 73 | `"01": {"texto": "Facturación", ...}` | Dict CAUSALES activo |
| `routes/pqrs.py` | 88-96 | `SUBCAUSALES_FACTURACION = {...}` | Dict activo |
| `routes/pqrs.py` | 135 | `"Facturación / Cobro"` | Dict COMPONENTES |
| `routes/pqrs.py` | 146 | `"F": {"nombre": "Facturación", ...}` | Dict GRUPO_CAUSALES |
| `routes/pqrs.py` | 226 | Referencia en función de carga | Lógica activa |
| `routes/pqrs.py` | 470 | Referencia CAUSALES dict | Lógica activa |
| `routes/pqrs.py` | 516 | Referencia CAUSALES dict | Lógica activa |
| `routes/pqrs.py` | 1056 | Referencia en reporte | Lógica activa |
| `routes/pqrs.py` | 1166 | Referencia en reporte | Lógica activa |
| `templates/pqrs/nueva.html` | 189 | `"Facturación"` en select option | UI visible |
| `templates/pqrs/nueva.html` | 191 | `"Facturación"` en label | UI visible |

**Origen:** Diccionarios normativos SSPD heredados — coexisten con la nueva jerarquía RC6 (migración 031). Los diccionarios SSPD no fueron eliminados al agregar el nuevo sistema de causales.

---

## PUNTO 8 — REFERENCIAS PROHIBIDAS: PRESIÓN

**Estado: ❌ FALLA CRÍTICA**

| Archivo | Línea | Contenido | Tipo |
|---|---|---|---|
| `routes/pqrs.py` | 710 | `pruebas_presion` | Campo en query/modelo |
| `routes/pqrs.py` | 719 | `pruebas_presion` | Campo en lógica activa |

`pruebas_presion` es un campo de calidad de agua normativa antigua que no corresponde a la arquitectura RC6. La Calidad del Agua en RC6 usa `Res. 2115/2007` con campo `ACEPTABLE/NO_ACEPTABLE` en `cal_resultados_fisicoquimicos`.

---

## PUNTO 9 — REFERENCIAS: CALIDAD DE AGUA ANTIGUA

**Estado: ✅ PASA (parcial)**

La entidad principal de Calidad del Agua fue migrada a `cal_muestras` y `cal_resultados_fisicoquimicos` con esquema Res.2115/2007. No se encontraron referencias al esquema antiguo en templates de calidad agua.

**Excepción documentada:** `pruebas_presion` en `pqrs.py` (cubierto en punto 8).

---

## PUNTO 10 — REFERENCIAS PQRS SSPD 01-99 (CAUSALES NORMATIVAS)

**Estado: ❌ FALLA CRÍTICA**

Los diccionarios normativos SSPD permanecen completamente activos en `routes/pqrs.py`:

```
CAUSALES = {
  "01": {"texto": "Facturación", ...},   # línea 73
  "02": ...,
  ...
}
SUBCAUSALES_FACTURACION = {...}          # líneas 88-96
COMPONENTES = {..., "Facturación/Cobro"} # línea 135
GRUPO_CAUSALES = {"F": "Facturación"...} # línea 146
```

La migración 031 agregó la nueva jerarquía RC6 (`gc_servicios → gc_tipo_solicitante → gc_medios_recepcion → gc_pqrs_causales`) pero NO eliminó los diccionarios SSPD. El formulario `nueva.html` muestra ambos sistemas simultáneamente — el antiguo (select SSPD) y el nuevo (radio servicio + causal cascada).

**Brecha adicional:** `fk_causal_id` (nuevo sistema RC6) se renderiza en el formulario pero NO se guarda al insertar en la tabla `gc_pqrs`. La columna para almacenarlo no existe en la tabla.

---

## PUNTO 11 — GE/GC/GF/GA/GL COMO ÚNICAS ÁREAS MAESTRAS

**Estado: ⚠️ ALERTA**

| Área | Blueprint | URL Base | Frontend | Estado |
|---|---|---|---|---|
| GE — Gobierno/Estratégico | Ninguno activo | — | No | ⚠️ Tablas sin frontend |
| GC — Comercial | `pqrs_bp`, `sus_bp`, `com_bp` | `/pqrs`, `/suscriptores`, `/comunicaciones` | Sí | ✅ |
| GF — Financiero | `fin_bp`, `inv_bp`, `conv_bp` | `/finanzas`, `/inventarios`, `/convenios` | Sí | ✅ |
| GA — Ambiental/Operativo | `gis_bp`, `cal_bp`, `bh_bp`, `ot_bp`, `proy2_bp` | Múltiples | Sí | ✅ |
| GL — Laboral | `lab_bp` | `/laboral` | Sí | ✅ |
| **PEC** | `em_bp` | `/emergencias` | Sí | ❌ Área no reconocida |

`em_bp` (`/emergencias`) actúa como área independiente fuera de GE/GC/GF/GA/GL. Según arquitectura RC6, PEC debe ser una instancia de proyecto dentro de GA-08.

---

## PUNTO 12 — PROYECTOS GENÉRICOS (PUEAA/PSMV/PEC COMO INSTANCIAS)

**Estado: ⚠️ ALERTA**

| Archivo | Línea | Referencia | Tipo | Estado |
|---|---|---|---|---|
| `routes/proyectos_v2.py` | 924-925 | PUEAA/PSMV como códigos de tipo | Instancias | ✅ Correcto |
| `routes/proyectos_v2.py` | 561, 731, 841 | "Metas PUEAA/PSMV" en labels | Informativo | ⚠️ Acoplado al tipo |
| `routes/reportes_normativos.py` | 113 | `@rep_bp.route("/pueaa/enviar_car")` | Endpoint normativo | ⚠️ Acoplamiento nombre |
| `routes/reportes_normativos.py` | 115 | `def enviar_pueaa()` | Función normativa | ⚠️ Acoplamiento nombre |
| `routes/emergencias.py` | Blueprint completo | PEC como módulo | **Módulo independiente** | ❌ Viola arquitectura |
| `templates/proyectos2/panel.html` | 61 | "PUEAA · PSMV · Obras" en título | Texto visible UI | ⚠️ Debería ser genérico |
| `templates/proyectos2/panel.html` | 81-82, 133-134 | PUEAA/PSMV en `<option>` value | Tipos en select | ✅ Correcto como instancias |

**Diagnóstico:** PUEAA y PSMV como *valores de tipo de proyecto* son correctos. El problema es PEC (`em_bp`) que vive fuera del módulo GA-08 y tiene su propia tabla `riesgos_pec` sin prefijo de área.

---

## MATRIZ DE TRAZABILIDAD COMPLETA

| # | Archivo | Línea(s) | Módulo/Área | Estado | Observación |
|---|---|---|---|---|---|
| 1 | `database/migrations/026_suscriptores_gc01.py` | — | GC | ✅ PASA | Migración presente en disco |
| 2 | `database/migrations/027_ordenes_trabajo_rc6.py` | — | GA | ✅ PASA | Migración presente en disco |
| 3 | `database/migrations/028_puntos_concertacion.py` | — | GA | ✅ PASA | Migración presente en disco |
| 4 | `database/migrations/029_personal_gl01.py` | — | GL | ✅ PASA | Migración presente en disco |
| 5 | `database/migrations/030_gobierno_ge01.py` | — | GE | ✅ PASA | Migración presente en disco |
| 6 | `database/migrations/031_pqrs_jerarquia.py` | — | GC | ✅ PASA | Migración presente en disco |
| 7 | `app.py` | 267-272 | Sistema | ✅ PASA | Migraciones 026-031 registradas en `_run_migrations()` |
| 8 | `app.py` | 46-48 | GC/GA/GL | ✅ PASA | sus_bp, ot_bp, lab_bp importados |
| 9 | `app.py` | 69-71 | GC/GA/GL | ✅ PASA | sus_bp, ot_bp, lab_bp registrados |
| 10 | `app.py` | 34 | GA | ❌ CRÍTICO | `proy_bp` v1 importado — módulo obsoleto activo |
| 11 | `app.py` | 57 | GA | ❌ CRÍTICO | `proy_bp` v1 registrado en `/proyectos` — ruta fantasma |
| 12 | `routes/proyectos.py` | Blueprint | GA | ❌ CRÍTICO | Proyectos v1 activo; debe eliminarse a favor de proy2_bp |
| 13 | `routes/emergencias.py` | Blueprint | Ninguna | ❌ CRÍTICO | `em_bp` PEC como módulo independiente — viola GE/GC/GF/GA/GL |
| 14 | `routes/pqrs.py` | 73 | GC | ❌ CRÍTICO | `CAUSALES["01"]` = "Facturación" — diccionario SSPD activo |
| 15 | `routes/pqrs.py` | 88-96 | GC | ❌ CRÍTICO | `SUBCAUSALES_FACTURACION` dict activo |
| 16 | `routes/pqrs.py` | 135 | GC | ❌ CRÍTICO | "Facturación / Cobro" en COMPONENTES activo |
| 17 | `routes/pqrs.py` | 146 | GC | ❌ CRÍTICO | `GRUPO_CAUSALES["F"]` = "Facturación" activo |
| 18 | `routes/pqrs.py` | 226, 470, 516, 1056, 1166 | GC | ❌ CRÍTICO | Lógica que consume diccionarios SSPD/Facturación activa |
| 19 | `routes/pqrs.py` | 710, 719 | GC | ❌ CRÍTICO | `pruebas_presion` campo activo — esquema antiguo |
| 20 | `templates/pqrs/nueva.html` | 189, 191 | GC | ❌ CRÍTICO | "Facturación" visible en UI del formulario PQRS |
| 21 | `templates/pqrs/nueva.html` | Form POST | GC | ❌ CRÍTICO | `fk_causal_id` (RC6) no se persiste — columna inexistente en tabla |
| 22 | `templates/base.html` | 107 | GA | ⚠️ ALERTA | `href="/proyectos2/"` hardcoded — no usa `url_for` |
| 23 | `templates/base.html` | Sidebar completo | Todos | ✅ PASA | 26 url_for verificados, todos con función destino existente |
| 24 | `templates/dashboard.html` | Template completo | Dashboard | ✅ PASA | KPI cards v3, sparklines, Estado Operativo — correcto |
| 25 | `templates/proyectos2/panel.html` | 61 | GA-08 | ⚠️ ALERTA | Título "PUEAA · PSMV · Obras" — debería ser genérico |
| 26 | `templates/proyectos2/panel.html` | 81-82, 133-134 | GA-08 | ✅ PASA | PUEAA/PSMV como valores de `<option>` — uso correcto como instancias |
| 27 | `routes/proyectos_v2.py` | 924-925 | GA-08 | ✅ PASA | PUEAA/PSMV como códigos de tipo — correcto |
| 28 | `routes/reportes_normativos.py` | 113, 115 | Reportes | ⚠️ ALERTA | `/pueaa/enviar_car` y `enviar_pueaa()` — acoplamiento nombre en endpoint normativo |
| 29 | `database/migrations/024_balance_hidrico_mensual.py` | tabla `niveles_quebrada` | GA | ⚠️ ALERTA | Nombre sin prefijo `ga_` |
| 30 | `database/migrations/028_puntos_concertacion.py` | tabla `ga_nivel_quebrada` | GA | ⚠️ ALERTA | **Duplicado** de `niveles_quebrada` — misma entidad, dos tablas |
| 31 | `routes/emergencias.py` | tabla `riesgos_pec` | Sin área | ❌ CRÍTICO | Tabla sin prefijo de área, entidad fuera de arquitectura RC6 |
| 32 | `database/migrations/030_gobierno_ge01.py` | `ge_actas`, `ge_resoluciones` | GE | ⚠️ ALERTA | Tablas creadas, ningún blueprint/frontend asociado (GE sin UI) |
| 33 | `static/css/estilo.css` | v3.0 completo | Sistema | ✅ PASA | Variables CSS, sidebar dark, KPI, responsive — conforme |
| 34 | `app.py` | 79-88 | Sistema | ✅ PASA | Context processor: `hoy`, `anio_actual`, `version`, `csrf_token` |
| 35 | `app.py` | 105-140 | Sistema | ✅ PASA | CSRF verificado en rutas de configuración y backup |

---

## RESUMEN DE HALLAZGOS POR SEVERIDAD

### ❌ CRÍTICOS (requieren corrección antes de producción)

1. **proy_bp v1 activo** (`app.py:34,57`) — Módulo proyectos versión 1 activo junto a v2. Rutas `/proyectos/*` accesibles pero sin sidebar entry (fantasmas).

2. **Diccionarios SSPD/Facturación activos** (`routes/pqrs.py:73,88-96,135,146`) — El sistema de causales SSPD normativo no fue desactivado al implementar la nueva jerarquía RC6. "Facturación" visible en UI.

3. **`pruebas_presion` activo** (`routes/pqrs.py:710,719`) — Campo de esquema anterior activo en lógica de PQRS.

4. **`fk_causal_id` sin persistencia** (`templates/pqrs/nueva.html` + tabla `gc_pqrs`) — El formulario RC6 Nivel 4 (causal) no guarda el valor. La columna no existe en la tabla destino.

5. **PEC como módulo independiente** (`routes/emergencias.py`) — `em_bp` en `/emergencias` no pertenece a ninguna área maestra. Viola estructura GE/GC/GF/GA/GL. Debería ser proyecto tipo PEC dentro de GA-08.

### ⚠️ ALERTAS (corrección recomendada)

6. **Tablas nivel quebrada duplicadas** — `niveles_quebrada` (mig024) y `ga_nivel_quebrada` (mig028) representan la misma entidad.

7. **GE sin frontend** — `ge_actas` y `ge_resoluciones` existen en BD pero ningún blueprint las expone.

8. **Título panel proyectos** (`templates/proyectos2/panel.html:61`) — "PUEAA · PSMV · Obras" en texto visible — no es genérico.

9. **Endpoint normativo con nombre específico** (`routes/reportes_normativos.py:113`) — `/pueaa/enviar_car` vincula nombre de programa al endpoint.

10. **href hardcoded proyectos2** (`templates/base.html:107`) — No usa `url_for`, inconsistente con el resto del sidebar.

### ✅ APROBADOS

- Migraciones 026-031: presentes en disco y registradas
- Blueprints sus_bp, ot_bp, lab_bp: importados y registrados
- Sidebar navigation: 26 url_for verificados, todos funcionales
- CSS v3.0: dark sidebar, KPI cards, responsive — conforme
- Dashboard: KPI v3, sparklines, Estado Operativo — correcto
- PUEAA/PSMV como *tipos* de proyecto en select options: uso correcto
- Calidad Agua: migrada a esquema Res.2115/2007 — sin referencias antiguas
- CSRF: verificado en configuración y backup

---

*Informe generado: 2026-06-13 · Solo lectura · Sin modificaciones de código*
