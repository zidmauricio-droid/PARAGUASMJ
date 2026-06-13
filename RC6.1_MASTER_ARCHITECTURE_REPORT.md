# RC6.1 — INFORME MAESTRO DE ARQUITECTURA
## PARAGUASMJ / SIGCA — Sistema Integral de Gestión para Acueductos Comunitarios

**Versión:** RC6.1  
**Fecha:** 2026-06-13  
**Estado:** Pendiente de Aprobación Institucional  
**Elaborado por:** Equipo Técnico SIGCA  
**Clasificación:** Documento Técnico Interno — Restringido  

---

## RESUMEN EJECUTIVO

El presente informe constituye el análisis arquitectónico completo del sistema PARAGUASMJ (SIGCA) en su transición hacia la versión RC6.1. El análisis parte de un inventario exhaustivo del estado actual del sistema — 19 blueprints, 283 endpoints, 63 tablas de base de datos y 46 plantillas HTML — y define con precisión técnica la arquitectura objetivo estructurada en cinco áreas institucionales: Gestión Estratégica (GE), Gestión Comercial (GC), Gestión Financiera (GF), Gestión Ambiental y Operativa (GA) y Gestión Laboral (GL).

PARAGUASMJ no es un software de facturación ni un ERP tradicional. Es un sistema de gestión integral diseñado exclusivamente para acueductos comunitarios rurales de Colombia, organismos regulados por la Ley 142 de 1994, la Resolución 2115 de 2007 del Ministerio de Salud, y los lineamientos de la Superintendencia de Servicios Públicos Domiciliarios (SSPD). Su naturaleza documental, operativa y ambiental exige una arquitectura que refleje la realidad institucional de estas organizaciones sin ánimo de lucro.

Este informe identifica los módulos que deben congelarse, fusionarse, eliminarse o crearse; define el mapa de migraciones 026-030; cuantifica el impacto en blueprints, rutas, menús, permisos, reportes, GIS y base de datos; y establece el cronograma de implementación por fases con sus criterios de aprobación.

El principio rector de RC6.1 es la **neutralidad de cliente**: ningún nombre de organización específica puede aparecer en el código fuente, plantillas, configuraciones ni archivos de datos del sistema. Los datos institucionales se configuran por instalación mediante la tabla `configuracion` y el módulo de logo/nombre institucional ya existente.

---

## PARTE 1 — DEFINICIÓN DEL SISTEMA

### 1.1 Naturaleza Institucional

PARAGUASMJ es un Sistema Integral de Gestión Documental, Operativa, Financiera, Ambiental, Técnica y Administrativa para Organizaciones Prestadoras de Servicios Públicos Domiciliarios de Acueducto y/o Alcantarillado de carácter comunitario en Colombia.

Las organizaciones usuarias del sistema son, típicamente:

- Asociaciones de Suscriptores de Acueductos Comunitarios (reguladas por Ley 142/1994, art. 15.4)
- Juntas Administradoras de Acueductos Veredales
- Organizaciones Comunitarias Prestadoras (OCP) según clasificación SSPD
- Empresas Comunitarias de Acueducto y Alcantarillado

Estas organizaciones tienen en común:
- Operación sin ánimo de lucro
- Gobernanza comunitaria (Asamblea General, Junta Directiva, Representante Legal)
- Obligaciones de reporte ante SSPD, CAR y CRA
- Operación técnica de sistemas de acueducto (captación, tratamiento, distribución)
- Gestión de suscriptores (usuarios del servicio)
- Administración financiera con recursos públicos y comunitarios

### 1.2 Marco Normativo Aplicable

| Norma | Organismo | Materia |
|---|---|---|
| Ley 142/1994 | Congreso | Régimen de SPD — define estructura organizacional |
| Res. 2115/2007 | Min. Salud/Min. Ambiente | Calidad del agua para consumo humano — parámetros |
| Res. 330/2017 | Min. Vivienda | Reglamento técnico para acueductos y alcantarillados |
| Res. SSPD 54575/2015 | SSPD | Clasificación de causales PQRS |
| Res. CRA 943/2021 | CRA | Metodología tarifaria acueductos comunitarios |
| Ley 1755/2015 | Congreso | Derecho de petición — SLA de PQRS |
| Dec. 1575/2007 | Min. Salud | Sistema para la protección y control de la calidad del agua |
| PUEAA (Res. 0330/2017) | Min. Vivienda | Plan de Uso Eficiente y Ahorro del Agua — obligatorio |
| PSMV | CARS | Plan de Saneamiento y Manejo de Vertimientos |

### 1.3 Principios Arquitectónicos No Negociables

1. **Neutralidad de cliente**: El sistema no contiene nombres de organizaciones específicas en código fuente ni plantillas. Solo en `configuracion`.
2. **Offline-first**: Toda funcionalidad opera sin conectividad a Internet. Sin CDN. Sin APIs externas en tiempo de ejecución.
3. **SQLite WAL**: Motor único de base de datos. Sin migraciones destructivas.
4. **Idempotencia**: Cada migración puede ejecutarse N veces sin efecto negativo.
5. **PyInstaller-compatible**: El sistema puede empaquetarse como ejecutable para distribución sin Python.
6. **Multicliente**: Una instalación = un acueducto. El sistema es configurable, no parametrizable por cliente en tiempo de ejecución compartido.
7. **Documental primero**: Todo proceso genera o consume documentos. El registro documental es la fuente de verdad.
8. **GIS como núcleo operativo**: La georeferenciación es el eje de la operación técnica.

---

## PARTE 2 — MAPA ACTUAL DEL SISTEMA (ESTADO RC6)

### 2.1 Inventario de Blueprints

El sistema cuenta actualmente con **19 blueprints** registrados en `app.py`:

| N° | Blueprint | Nombre Interno | URL Prefix | Rutas | Área RC6 |
|---|---|---|---|---|---|
| 1 | auth_bp | autenticacion | (raíz) | 18 | Transversal |
| 2 | dash_bp | dashboard | (raíz) | 3 | GE |
| 3 | docs_bp | documentos | /documentos | 45 | GE-05 |
| 4 | pqrs_bp | pqrs | /pqrs | 18 | GC-02 |
| 5 | gis_bp | gis | /gis | 12 | GA-08 |
| 6 | bh_bp | balance_hidrico | /balance | 9 | GA-03 |
| 7 | com_bp | comunicaciones | /comunicaciones | 2 | GC/GE |
| 8 | proy_bp | proyectos | /proyectos | 6 | GA (v1 legacy) |
| 9 | api_bp | api | /api | 12 | Transversal |
| 10 | fin_bp | finanzas | /finanzas | 19 | GF |
| 11 | rep_bp | reportes_normativos | /reportes | 9 | GE-03/GF |
| 12 | aud_bp | auditoria | /auditoria | 13 | GE-03 |
| 13 | proy2_bp | proyectos2 | /proyectos2 | 27 | GA-08 |
| 14 | em_bp | emergencias | /emergencias | 25 | GA-04/05 |
| 15 | conv_bp | convenios | /convenios | 9 | GF-04 |
| 16 | carpetas_bp | carpetas | /carpetas | 9 | GE-05 |
| 17 | expedientes_bp | expedientes | /expedientes | 7 | GE-05 |
| 18 | cal_bp | calidad_agua | /calidad-agua | 9 | GA-02 |
| 19 | inv_bp | inventarios | /inventarios | 6 | GF-05 |
| — | app.py directo | — | /configuracion, /backup, etc. | 5 | Admin |

**Total: 283 endpoints**

### 2.2 Inventario de Tablas de Base de Datos

#### 2.2.1 Tablas Base (inicializar_db.py) — 40 tablas

| Grupo | Tablas |
|---|---|
| Identidad y Acceso | `organizaciones`, `usuarios`, `sesiones_log` |
| Contactos/Partes | `contactos` |
| Gestión Documental | `registro_central`, `contenido_documento`, `seguimiento_documento`, `documentos_adjuntos`, `plazos_documento`, `control_consecutivos` |
| Firmas y OTP | `firmantes`, `reglas_firmantes`, `autorizaciones_otp`, `acciones_pendientes` |
| PQRS | `pqrs`, `comunicaciones_recibidas` |
| Proyectos v1 | `proyectos`, `actividades`, `presupuesto_rubros`, `cotizaciones`, `ordenes_compra_productos`, `tareas` |
| Operación | `ordenes_trabajo`, `ordenes_salida`, `actas_ejecucion` |
| Agua y Ambiente | `lecturas_macromedicion`, `balance_hidrico`, `indicadores_mensuales`, `riesgos` |
| Finanzas | `bancos`, `movimientos_financieros`, `caja_chica` |
| GIS | `zonas_prestacion`, `gis_infraestructura`, `gis_suscriptores_posicion`, `gis_reportes_fallas` |
| Sistema | `configuracion`, `configuracion_historial`, `notificaciones_historial`, `logs_sistema` |

#### 2.2.2 Tablas por Migraciones (016-025) — 23 tablas adicionales

| Migración | Tablas Creadas | Área RC6 |
|---|---|---|
| 018 | `pqrs_causales_sspd` | GC-02 |
| 021 | `tipos_proyecto` | GA-08 |
| 022 | `areas_institucionales`, `subareas_institucionales`, `pqrs_series_causales`, `pqrs_causales_rc6`, `suscriptores_registro`, `inventario_items`, `inventario_movimientos` | Transversal |
| 023 | `calidad_parametros`, `calidad_puntos_muestreo`, `calidad_muestras`, `calidad_resultados` | GA-02 |
| 024 | `bh_macromedidor_mensual`, `bh_nivel_quebrada`, `bh_resumen_mensual` | GA-03 |
| 025 | `fin_plan_cuentas`, `fin_transacciones`, `fin_presupuesto` | GF |

**Total: 63 tablas activas**

### 2.3 Inventario de Plantillas

El sistema cuenta con **46 archivos HTML** organizados en 15 directorios bajo `templates/`. La plantilla base `base.html` contiene la barra de navegación principal, el procesamiento de mensajes flash, el pie de página institucional y los scripts globales (Bootstrap 5.3.2 local, TipTap 2.4 local).

### 2.4 Estado del Menú de Navegación Actual

El menú actual (`base.html`) tiene la siguiente estructura:

```
Panel
Documentos → [Todos / Nuevo]
PQRS
Comunicaciones
GA → [GA-02 Calidad Agua / GA-03 Balance Hídrico / GA-08 GIS / GA-09 Proyectos]
GF → [GF-06 Caja / GF-02 Bancos / GF-02 Movimientos / GF-05 Inventarios / GF-04 Convenios / GF Transacciones / Plan de Cuentas]
Reportes → [CAR/SSPD/CRA / Backup]
Admin → [Usuarios / Auditoría / Configuración / Diagnóstico]
```

**Problemas detectados:**
- GE (Gestión Estratégica) no existe como menú diferenciado
- GC (Gestión Comercial) no existe como agrupación — PQRS está suelto
- GL (Gestión Laboral) no existe en absoluto
- GF tiene ítems duplicados (GF-02 aparece dos veces como "Bancos" y "Movimientos" y también como "Transacciones")
- Emergencias no aparece en menú principal
- Suscriptores (GC-01) no tiene módulo activo
- GA-07 Órdenes de Trabajo no aparece en menú

---

## PARTE 3 — DIAGNÓSTICO POR ÁREA

### 3.1 GE — Gestión Estratégica

**Estado:** Parcialmente implementado bajo nombres genéricos.

| Subárea | Estado Actual | Módulo Existente | Brecha |
|---|---|---|---|
| GE-01 Gobierno Corporativo | Inexistente | — | Crear: Actas de Asamblea, Resoluciones, Acuerdos |
| GE-02 Planeación | Parcial | `proyectos_v2` (inadecuado) | Separar: planeación estratégica vs proyectos operativos |
| GE-03 Control Interno | Parcial | `auditoria` (logs técnicos) | Ampliar: auditoría documental, control de gestión |
| GE-04 Jurídica | Inexistente | `convenios` (parcial) | Crear: gestión jurídica integral |
| GE-05 Gestión Documental | Implementado | `documentos`, `expedientes`, `carpetas` | Consolidar: árbol de series TRD |

**Calificación:** 40% implementado

**Acciones RC6.1:**
- Crear blueprint `ge_bp` que consolide gobierno corporativo y planeación estratégica
- El blueprint `auditoria` se convierte en GE-03 con funciones de control interno además de logs
- El blueprint `convenios` migra a GF-04 (Contratación) pero mantiene enlace con GE-04

### 3.2 GC — Gestión Comercial

**Estado:** Fragmentado. El módulo central (suscriptores) no existe funcionalmente.

| Subárea | Estado Actual | Módulo Existente | Brecha |
|---|---|---|---|
| GC-01 Suscriptores | Datos en `contactos` sin módulo propio | — | Crear: módulo completo de suscriptores con `suscriptores_registro` |
| GC-02 PQRS | Implementado con limitaciones | `pqrs` | Mejorar: jerarquía 5 niveles, catálogo RC6 |
| GC-03 Cartera | Inexistente | — | Crear: control de mora, acuerdos de pago |
| GC-04 Conexiones | Inexistente | Datos dispersos en GIS/contactos | Crear: gestión de nuevas conexiones |
| GC-05 Fraudes | Inexistente | `gis_reportes_fallas` (inadecuado) | Crear: registro y seguimiento de fraudes |

**Calificación:** 20% implementado

**Acciones RC6.1:**
- Crear blueprint `suscriptores_bp` (GC-01) — PRIORIDAD ALTA
- Mejorar `pqrs_bp` con nueva jerarquía y catálogo de causales RC6
- GC-03 a GC-05: diferir a RC6.2/RC6.3

### 3.3 GF — Gestión Financiera

**Estado:** Implementado parcialmente con duplicación de funcionalidades.

| Subárea | Estado Actual | Módulo Existente | Brecha |
|---|---|---|---|
| GF-01 Presupuesto | Parcial | `fin_presupuesto` (migración 025) | Ampliar: ejecución presupuestal, vigencias |
| GF-02 Tesorería | Implementado | `finanzas.bancos`, `finanzas.movimientos`, `fin_transacciones` | Consolidar: comprobantes ingreso/egreso, conciliación |
| GF-03 Contabilidad | Parcial | `fin_plan_cuentas`, `fin_transacciones` | Ampliar: estado de resultados, flujo de caja mensual |
| GF-04 Contratación | Parcial | `convenios` | Migrar y ampliar: contratos, adiciones, pólizas |
| GF-05 Inventarios | Implementado | `inventarios` (inv_bp) | Completar: activos fijos, depreciación |
| GF-06 Caja | Implementado | `finanzas.caja` (caja_chica) | OK — mantener |

**Calificación:** 60% implementado

**Acciones RC6.1:**
- Eliminar duplicación: `movimientos_financieros` (tabla base) y `fin_transacciones` (migración 025) cumplen funciones similares — consolidar en `fin_transacciones`
- Agregar comprobantes de egreso/ingreso al módulo de tesorería
- GF-03 contabilidad: agregar exportación de estado de resultados mensual

### 3.4 GA — Gestión Ambiental y Operativa

**Estado:** El área más desarrollada. Requiere reestructuración de denominaciones.

| Subárea | Estado Actual | Módulo Existente | Brecha |
|---|---|---|---|
| GA-01 Operación | Parcial | `ordenes_trabajo` (tabla base) | Crear: panel operativo diario |
| GA-02 Calidad Agua | Implementado | `calidad_agua` (cal_bp) | Completar: integración GIS, reportes CAR |
| GA-03 Balance Hídrico | Implementado | `balance_hidrico` (bh_bp) | Completar: IANC automático, curva nivel quebrada |
| GA-04 Infraestructura | Parcial | `gis_infraestructura` | Ampliar: fichas técnicas, mantenimiento |
| GA-05 Mantenimiento | Parcial | `emergencias` (mal nombrado) | Renombrar y reestructurar |
| GA-06 Cuenca Hidrográfica | Inexistente | `gis_reportes_fallas` (parcial) | Crear: puntos de concertación, monitoreo |
| GA-07 Órdenes de Trabajo | Parcial | `ordenes_trabajo`, `ordenes_salida`, `actas_ejecucion` | Crear: blueprint dedicado GA-07 |
| GA-08 Proyectos | Implementado | `proyectos_v2` (proy2_bp) | Consolidar: fusionar proyectos v1 + v2 |
| GA-09 PSMV | Inexistente como módulo | Tipo en `tipos_proyecto` | Solo clasificación, no módulo independiente |

**Calificación:** 55% implementado

**Acciones RC6.1:**
- El blueprint `emergencias` debe renombrarse o absorberse en GA-04/GA-05
- Crear blueprint `ordenes_trabajo_bp` dedicado (GA-07)
- Fusionar `proyectos` (v1, 6 rutas) + `proyectos2` (v2, 27 rutas) en un solo blueprint GA-08
- Agregar tabla `ga_puntos_concertacion` para GA-06

### 3.5 GL — Gestión Laboral

**Estado:** No implementado. Completamente ausente.

| Subárea | Estado Actual | Módulo Existente | Brecha |
|---|---|---|---|
| GL-01 Personal | Inexistente | Datos en `contactos` (tipo='Personal') | Crear: ficha de personal, contratos laborales |
| GL-02 Selección | Inexistente | — | Diferir RC6.3 |
| GL-03 Evaluación | Inexistente | — | Diferir RC6.3 |
| GL-04 Capacitación | Inexistente | — | Diferir RC6.3 |
| GL-05 SST | Inexistente | — | Diferir RC6.3 |

**Calificación:** 0% implementado

**Acciones RC6.1:** Crear estructura mínima GL-01 (directorio de personal). GL-02 a GL-05 difieren a versiones posteriores.

---

## PARTE 4 — ANÁLISIS DE BRECHA (GAP ANALYSIS)

### 4.1 Módulos que Deben Congelarse

Los siguientes módulos están funcionalmente completos para RC6.1 y no requieren cambios en esta fase:

| Módulo | Blueprint | Justificación |
|---|---|---|
| Autenticación | auth_bp | OTP, perfiles, logo dinámico — completo |
| Gestión Documental | docs_bp | 45 rutas, TipTap, firmas, expedientes — maduro |
| Caja Menor | finanzas.caja | Funcional, auditado, con exportación Excel |
| Inventarios | inv_bp | Implementado RC6 con alertas de stock |
| Calidad del Agua | cal_bp | Implementado RC6 con Res. 2115/2007 |
| Balance Hídrico | bh_bp | Implementado RC6 con macromedición mensual |
| Diagnóstico | auditoria.diagnosticos | Implementado RC5.5.3, sin psutil |

### 4.2 Módulos que Deben Fusionarse

| Módulos a Fusionar | Resultado | Justificación |
|---|---|---|
| `proyectos` (v1) + `proyectos2` (v2) | `ga_proyectos_bp` | Duplicación. v1 tiene 6 rutas legacy; v2 tiene 27 activas |
| `bancos` + `movimientos` (en fin_bp) + `fin_transacciones` | GF-02 Tesorería unificada | Tres implementaciones del mismo concepto |
| `carpetas_bp` + `expedientes_bp` | Parte de GE-05 | Ambos gestionan estructura física documental |
| `comunicaciones` | Absorber en GE-05 | Solo 2 rutas — no justifica blueprint separado |

### 4.3 Módulos que Deben Eliminarse

| Módulo | Razón | Acción |
|---|---|---|
| Proyectos v1 (`proy_bp`) | Reemplazado por v2 | Desregistrar blueprint, mantener tablas por compatibilidad |
| `comunicaciones_recibidas` como módulo standalone | Funcionalidad cubierta por documentos | Absorber en GE-05 |
| `presupuesto_rubros` (tabla v1) | Reemplazada por `fin_presupuesto` (025) | Deprecar tabla, migrar datos |

### 4.4 Módulos que Deben Crearse en RC6.1

| Módulo | Blueprint | Prioridad | Área |
|---|---|---|---|
| Suscriptores | `suscriptores_bp` | ALTA | GC-01 |
| Órdenes de Trabajo | `ordenes_trabajo_bp` | ALTA | GA-07 |
| Tesorería Unificada | (refactor fin_bp) | MEDIA | GF-02 |
| Personal Básico | `laboral_bp` (GL-01) | BAJA | GL-01 |
| Puntos de Concertación | (extensión gis_bp) | MEDIA | GA-06 |

### 4.5 Módulos que Deben Separarse

| Módulo Actual | Separación | Justificación |
|---|---|---|
| `emergencias` (25 rutas mezcladas) | GA-04 Infraestructura + GA-05 Mantenimiento | El nombre "emergencias" no refleja la gestión de activos e infraestructura |
| `auditoria` (logs + usuarios + diagnóstico) | GE-03 Control Interno + Admin técnico | Mezcla auditoría documental con gestión de usuarios del sistema |
| `reportes_normativos` | GE-03 Reportes CAR/SSPD + GF-03 Reportes Financieros | Dos naturalezas distintas de reporte |

---

## PARTE 5 — MAPA OBJETIVO RC6.1

### 5.1 Estructura de Blueprints Objetivo

La arquitectura objetivo de RC6.1 tendrá **22 blueprints** (19 actuales + 3 nuevos, tras fusionar 2):

| N° | Blueprint | Área RC6 | URL Prefix | Estado |
|---|---|---|---|---|
| 1 | auth_bp | Transversal | / | Congelar |
| 2 | dash_bp | GE | / | Ampliar KPIs |
| 3 | docs_bp | GE-05 | /documentos | Congelar |
| 4 | carpetas_bp | GE-05 | /carpetas | Fusionar con expedientes |
| 5 | expedientes_bp | GE-05 | /expedientes | Fusionar con carpetas |
| 6 | auditoria_bp | GE-03 | /auditoria | Ampliar |
| 7 | suscriptores_bp | GC-01 | /suscriptores | CREAR |
| 8 | pqrs_bp | GC-02 | /pqrs | Ampliar jerarquía |
| 9 | comunicaciones_bp | GC/GE | /comunicaciones | Absorber o mantener mínimo |
| 10 | fin_bp | GF-01/02/03/06 | /finanzas | Ampliar tesorería |
| 11 | convenios_bp | GF-04 | /convenios | Mantener |
| 12 | inv_bp | GF-05 | /inventarios | Congelar |
| 13 | gis_bp | GA-08 núcleo | /gis | Ampliar capas |
| 14 | cal_bp | GA-02 | /calidad-agua | Congelar |
| 15 | bh_bp | GA-03 | /balance | Congelar |
| 16 | ga_proyectos_bp | GA-08 | /proyectos | FUSIÓN v1+v2 |
| 17 | ordenes_trabajo_bp | GA-07 | /ordenes-trabajo | CREAR |
| 18 | ga_infraestructura_bp | GA-04/05 | /infraestructura | RENOMBRAR emergencias |
| 19 | rep_bp | GE-03/GF | /reportes | Mantener |
| 20 | api_bp | Transversal | /api | Ampliar |
| 21 | laboral_bp | GL-01 | /laboral | CREAR mínimo |
| 22 | ge_bp | GE-01/02/04 | /gobierno | CREAR |

### 5.2 Menú de Navegación Objetivo

```
Panel de Control
├── GE — Gestión Estratégica
│   ├── GE-01 Gobierno Corporativo
│   ├── GE-02 Documentos (→ /documentos)
│   ├── GE-03 Control / Reportes
│   └── GE-04 Contratos/Jurídica
├── GC — Gestión Comercial
│   ├── GC-01 Suscriptores
│   ├── GC-02 PQRS
│   └── GC-03 Cartera (futuro)
├── GF — Gestión Financiera
│   ├── GF-01 Presupuesto
│   ├── GF-02 Tesorería (Bancos + Transacciones)
│   ├── GF-03 Contabilidad (Plan de Cuentas + Estado Resultados)
│   ├── GF-04 Contratos/Convenios
│   ├── GF-05 Inventarios
│   └── GF-06 Caja Menor
├── GA — Gestión Ambiental
│   ├── GA-02 Calidad del Agua
│   ├── GA-03 Balance Hídrico
│   ├── GA-07 Órdenes de Trabajo
│   ├── GA-08 Proyectos (PUEAA, PSMV, Obras...)
│   └── GA-08 Mapa GIS
├── GL — Gestión Laboral
│   └── GL-01 Personal
├── Reportes
└── Admin
```

---

## PARTE 6 — IMPACTO TÉCNICO DETALLADO

### 6.1 Impacto en Flask / Blueprints

**Cambios en app.py:**

El archivo `app.py` debe actualizarse para:

1. Desregistrar `proy_bp` (proyectos v1 — legacy)
2. Registrar `suscriptores_bp` (nuevo)
3. Registrar `ordenes_trabajo_bp` (nuevo)
4. Registrar `laboral_bp` (nuevo, mínimo)
5. Registrar `ge_bp` (nuevo, gobierno corporativo)
6. Renombrar o reemplazar `em_bp` → `ga_infraestructura_bp`

El sistema de migraciones en `_run_migrations()` debe agregar las entradas 026-030.

**Impacto en importaciones:**

Cada nuevo blueprint requiere:
- Archivo de ruta en `routes/`
- Al menos un template en `templates/[nombre]/`
- Registro en la lista de migraciones si crea tablas

### 6.2 Impacto en Rutas

**Rutas a crear (estimado RC6.1):**

| Módulo | Rutas Nuevas (estimado) | Tipo |
|---|---|---|
| GC-01 Suscriptores | 15 | CRUD + API |
| GA-07 Órdenes de Trabajo | 12 | CRUD + ciclo de vida |
| GF-02 Tesorería ampliada | 6 | Comprobantes, conciliación |
| GE-01 Gobierno Corporativo | 8 | Actas, resoluciones |
| GL-01 Personal mínimo | 8 | Directorio de personal |
| GA-06 Puntos de concertación | 5 | GIS + CRUD |

**Total estimado de rutas nuevas en RC6.1: ~54**

**Total proyectado del sistema: ~337 endpoints**

**Rutas a eliminar:**

| Ruta | Blueprint | Razón |
|---|---|---|
| `/proyectos/` (v1) | proy_bp | Sustituida por /proyectos2/ |
| `/proyectos/nuevo` (v1) | proy_bp | Sustituida |
| Todas las rutas v1 de proyectos | proy_bp | 6 rutas a desregistrar |

### 6.3 Impacto en Seguridad y Permisos

El sistema tiene 6 roles de usuario definidos en la tabla `usuarios`:

| Rol | Acceso Actual | Ajuste RC6.1 |
|---|---|---|
| `admin` | Total | Sin cambio |
| `presidente` | Aprobación documental | Agregar: aprobación órdenes de trabajo |
| `tesorera` | Finanzas completo | Agregar: GF-02 tesorería ampliada |
| `secretaria` | Documentos + PQRS | Agregar: GC-01 suscriptores (lectura) |
| `auxiliar` | Lectura + GA | Agregar: GA-07 órdenes de trabajo básico |
| `tecnico` | GA operativo | Sin cambio |

**Decoradores afectados:**

El decorador `@rol_requerido` debe aplicarse en todos los endpoints nuevos. En RC6.1 se propone agregar el rol `operador_comercial` para GC-01/GC-02 y `operador_laboral` para GL.

### 6.4 Impacto en el Sistema de Caché y Métricas

El módulo `core/metrics.py` con `@medir_tiempo` debe aplicarse a los nuevos endpoints críticos:
- `suscriptores.listar` (consultas de suscriptores pueden ser lentas con >500 registros)
- `ordenes_trabajo.listar` (JOIN con múltiples tablas)
- `gis.api_infraestructura` (carga GeoJSON completo)

El módulo `core/system_diagnostics.py` debe ampliar `_TABLAS_MONITOREADAS` con las tablas nuevas de RC6.1.

---

## PARTE 7 — IMPACTO EN BASE DE DATOS

### 7.1 Tablas a Crear en Migraciones 026-030

#### Migración 026 — Suscriptores GC-01

```
gc_suscriptores
  pk_suscriptor_id, fk_contacto_id, codigo_suscriptor,
  numero_medidor, fecha_conexion, tipo_suscriptor,
  estado (ACTIVO/SUSPENDIDO/CORTADO/INACTIVO),
  estrato, zona_prestacion, aforo_m3, observaciones,
  coordenada_lat, coordenada_lon, fk_zona_id,
  fecha_ultimo_pago, saldo_cartera, fecha_creacion

gc_conexiones
  pk_conexion_id, fk_suscriptor_id, tipo (NUEVA/RECONEXION/CORTE),
  fecha_solicitud, fecha_ejecucion, estado, valor_cobrado,
  tecnico_asignado, observaciones, fk_documento_id
```

#### Migración 027 — Órdenes de Trabajo GA-07 (refactor)

Las tablas `ordenes_trabajo`, `ordenes_salida` y `actas_ejecucion` ya existen en la BD base pero no tienen blueprint dedicado. La migración 027 agrega:

```
ga_ot_materiales_utilizados
  pk_mat_id, fk_ot_id, fk_item_inventario_id,
  cantidad_usada, unidad, fecha_uso, observaciones

ga_ot_imagenes
  pk_img_id, fk_ot_id, ruta_archivo, descripcion, fecha_captura
```

#### Migración 028 — Puntos de Concertación GA-06

```
ga_puntos_concertacion
  pk_punto_id, codigo, nombre, descripcion,
  coordenada_lat, coordenada_lon, estado,
  fecha_certificacion, fecha_vencimiento,
  entidad_certificadora, observaciones,
  fk_zona_id, activo, fecha_creacion
```

#### Migración 029 — Personal Básico GL-01

```
gl_personal
  pk_personal_id, fk_contacto_id, cargo, tipo_contrato,
  fecha_ingreso, fecha_retiro, salario_base, estado (ACTIVO/INACTIVO),
  numero_contrato, eps, arl, fondo_pension,
  observaciones, fecha_creacion
```

#### Migración 030 — Gobierno Corporativo GE-01

```
ge_actas
  pk_acta_id, tipo (ASAMBLEA/JUNTA/COMITE/EXTRAORDINARIA),
  numero_acta, fecha_reunion, lugar, quorum_requerido, quorum_presente,
  orden_del_dia, decisiones, estado (BORRADOR/APROBADA/ARCHIVADA),
  fk_documento_id, fk_creador_id, fecha_creacion

ge_resoluciones
  pk_resolucion_id, numero, anio, fecha_expedicion,
  asunto, descripcion, estado (VIGENTE/DEROGADA/SUSPENDIDA),
  fk_documento_id, fecha_creacion
```

### 7.2 Tablas a Modificar

| Tabla | Columnas a Agregar | Migración |
|---|---|---|
| `ordenes_trabajo` | `fk_ga_punto_id`, `fk_suscriptor_id` | 027 |
| `gis_infraestructura` | `fk_ga_punto_id`, `estado_operativo` | 027 |
| `pqrs` | `fk_suscriptor_id`, `nivel1`, `nivel2`, `nivel3`, `medio_recepcion_rc6` | 026 |
| `contactos` | `fk_suscriptor_id` (referencia cruzada) | 026 |

### 7.3 Tablas a Deprecar

| Tabla | Estado | Plan |
|---|---|---|
| `proyectos` (v1) | Deprecar | Mantener datos, redirigir UI a proyectos2 |
| `actividades` (v1) | Deprecar | Mantener datos históricos |
| `presupuesto_rubros` (v1) | Deprecar | Migrar datos a `fin_presupuesto` |
| `lecturas_macromedicion` (diarias) | Deprecar | Sustituida por `bh_macromedidor_mensual` |

### 7.4 Índices a Crear en Migraciones 026-030

```sql
-- Migración 026
CREATE INDEX idx_gc_suscriptores_codigo ON gc_suscriptores(codigo_suscriptor);
CREATE INDEX idx_gc_suscriptores_estado ON gc_suscriptores(estado);
CREATE INDEX idx_gc_conexiones_suscriptor ON gc_conexiones(fk_suscriptor_id);

-- Migración 027
CREATE INDEX idx_ga_ot_materiales_ot ON ga_ot_materiales_utilizados(fk_ot_id);
CREATE INDEX idx_ordenes_trabajo_estado ON ordenes_trabajo(estado);

-- Migración 028
CREATE INDEX idx_ga_conc_estado ON ga_puntos_concertacion(estado);

-- Migración 029
CREATE INDEX idx_gl_personal_estado ON gl_personal(estado);
CREATE INDEX idx_gl_personal_cargo ON gl_personal(cargo);
```

---

## PARTE 8 — IMPACTO EN REPORTES NORMATIVOS

### 8.1 Reportes CAR (Corporación Autónoma Regional)

Los reportes CAR actuales generados por `reportes_normativos.py` incluyen:

- **Balance Hídrico Mensual**: Consumos por zona, IANC, comparativo con macromedidor
- **PUEAA** (Plan de Uso Eficiente del Agua): Indicadores IPAA, IMA, POAC, IRAC
- **Calidad del Agua**: Resultados por punto de muestreo, parámetros Res. 2115/2007

**Impacto RC6.1:**
- El reporte de Calidad del Agua debe consumir `calidad_muestras` + `calidad_resultados` (migración 023) — actualmente puede estar usando la tabla legacy
- Agregar reporte de Puntos de Concertación (migración 028) como requisito de algunas CARs
- Los reportes PUEAA deben migrar de proyectos v1 a proyectos v2 como fuente de datos

### 8.2 Reportes SSPD

El reporte SUI-FC-15 debe incluir:

- PQRS por causal RC6 (catálogo de causales migración 022)
- Tiempos de respuesta vs. SLA Ley 1755/2015
- Clasificación por servicio (ACUEDUCTO/ALCANTARILLADO)
- Clasificación por tipo de solicitante (SUSCRIPTOR/USUARIO/TERCERO)

**Impacto RC6.1:**
- El formulario de PQRS debe capturar los campos `nivel1` (servicio), `nivel2` (tipo_solicitante), `nivel3` (medio_recepcion_rc6)
- Los reportes exportados en CSV para SUI deben usar la codificación oficial de causales SSPD

### 8.3 Reportes CRA (Comisión de Regulación de Agua)

Los indicadores financieros reportados a CRA incluyen:

- IUS (Índice de Uso del Servicio) — implementado en `core/indicadores_ius.py`
- Tarifa vigente vs. tarifa regulada
- Estado de cartera

**Impacto RC6.1:**
- El módulo GC-03 Cartera (a crear en RC6.2) alimentará directamente estos reportes
- El plan de cuentas `fin_plan_cuentas` (migración 025) debe mapearse a las cuentas del SUI financiero

---

## PARTE 9 — IMPACTO EN GIS

### 9.1 GIS como Núcleo Operativo

El mapa GIS (`gis_bp`, `/gis/mapa`) es actualmente un mapa Leaflet con capas de infraestructura, suscriptores y fallas. En RC6.1 debe convertirse en el **núcleo operativo** del área GA.

### 9.2 Capas GIS Objetivo RC6.1

| Capa | Tabla Fuente | Estado | Módulo Consumidor |
|---|---|---|---|
| Infraestructura | `gis_infraestructura` | Implementada | GA-04 |
| Suscriptores | `gis_suscriptores_posicion` + `gc_suscriptores` | Parcial | GC-01 |
| Fallas/Incidentes | `gis_reportes_fallas` | Implementada | GA-05 |
| Puntos de Concertación | `ga_puntos_concertacion` | CREAR | GA-06 |
| Calidad del Agua | `calidad_puntos_muestreo` | Crear capa | GA-02 |
| Órdenes de Trabajo | `ordenes_trabajo` con coordenadas | Crear capa | GA-07 |

### 9.3 Extensión del API GIS

Se deben agregar los siguientes endpoints al blueprint `gis_bp`:

```
GET  /gis/api/puntos-concertacion
POST /gis/api/puntos-concertacion
PUT  /gis/api/puntos-concertacion/<id>
GET  /gis/api/calidad-agua/geojson
GET  /gis/api/ordenes-trabajo/activas
GET  /gis/api/resumen-operativo
```

### 9.4 Puntos de Concertación — Estructura Técnica

Los puntos de concertación son ubicaciones donde la organización prestadora y la comunidad o entidad regulatoria acuerdan monitorear el recurso hídrico. Cada punto debe tener:

- Código único (formato: PC-001, PC-002...)
- Nombre descriptivo
- Coordenadas GPS (lat/lon decimal)
- Estado: ACTIVO, SUSPENDIDO, VENCIDO, CERTIFICADO
- Fecha de certificación y vencimiento
- Entidad certificadora (la CAR correspondiente)
- Historial de mediciones (vinculado a GA-03 Balance Hídrico y GA-02 Calidad del Agua)
- Representación en mapa con ícono diferenciado

---

## PARTE 10 — IMPACTO DOCUMENTAL

### 10.1 Árbol de Series Documentales TRD

El sistema tiene una Tabla de Retención Documental (TRD) cargada en `config/trd.json`. Las series documentales deben alinearse con las cinco áreas RC6:

| Área | Series TRD | Código |
|---|---|---|
| GE — Estratégica | Actas de Asamblea, Actas de Junta, Resoluciones, Contratos, Convenios | GE-ACT, GE-RES, GE-CON |
| GC — Comercial | PQRS, Contratos de Suscripción, Órdenes de Conexión | GC-PQRS, GC-CON |
| GF — Financiera | Comprobantes, Extractos, Pólizas, Informes Financieros | GF-COMP, GF-INF |
| GA — Ambiental | Informes de Calidad, Reportes Balance Hídrico, Actas OT, Informes CAR | GA-ICA, GA-BAL, GA-OT |
| GL — Laboral | Contratos de Trabajo, Nóminas, Evaluaciones | GL-CT, GL-NOM |

### 10.2 Nomenclatura Documental

La convención de nombres actual en `control_consecutivos` es:

```
{AREA}-{TIPO}-{ANIO}-{CONSECUTIVO}
Ejemplo: GA-OFI-2026-001
```

En RC6.1 se extiende a subárea:

```
{AREA}-{SUBAREA}-{TIPO}-{ANIO}-{CONSECUTIVO}
Ejemplo: GC-02-PQRS-2026-001
         GF-02-COMP-2026-015
         GA-07-OT-2026-088
```

### 10.3 Flujo Documental por Área

#### Flujo GE-05 (Documentos Formales)
```
Borrador → Revisión → Aprobación (OTP) → Firmado → Archivado → TRD
```

#### Flujo GC-02 (PQRS)
```
Recepción → Clasificación (5 niveles) → Asignación → Respuesta → Notificación → Archivado
```

#### Flujo GF-02 (Tesorería)
```
Solicitud de Pago → Comprobante de Egreso → Aprobación → Ejecución → Conciliación → Archivado
```

#### Flujo GA-07 (Órdenes de Trabajo)
```
Solicitud/Falla → OT Creada → Asignación → Ejecución → Acta → Cierre → Archivado
```

### 10.4 Documentos Vinculados a Módulos

| Módulo | Tipo de Documento Generado | Template |
|---|---|---|
| PQRS | Acuse de recibo, Respuesta oficial | GC-PQRS |
| Órdenes de Trabajo | Acta de ejecución, Informe técnico | GA-OT |
| Calidad del Agua | Informe de análisis, Reporte CAR | GA-ICA |
| Balance Hídrico | Informe mensual IANC, Reporte CAR | GA-BAL |
| Finanzas | Comprobante ingreso/egreso | GF-COMP |
| Suscriptores | Contrato de suscripción, Notificación | GC-CON |
| Proyectos | Acta de inicio, Informe de avance, Acta de cierre | GA-08 |

---

## PARTE 11 — PQRS — NUEVA JERARQUÍA RC6.1

### 11.1 Estructura de Cinco Niveles

La estructura actual de PQRS usa el catálogo SSPD heredado (Res. 54575/2015) con grupos F/I/P/O. En RC6.1 se adopta una jerarquía propia adaptada a la realidad del acueducto comunitario:

**Nivel 1 — Servicio:**
- ACUEDUCTO
- ALCANTARILLADO
- SERVICIO GENERAL

**Nivel 2 — Tipo de Solicitante:**
- SUSCRIPTOR (tiene contrato activo)
- USUARIO (beneficiario sin contrato directo)
- TERCERO (entidad, vecino, autoridad)

**Nivel 3 — Medio de Recepción:**
- PRESENCIAL
- CORREO ELECTRONICO
- WHATSAPP
- TELEFONO
- WEB
- OFICIO

**Nivel 4 — Tipo de Solicitud:**
- PETICION
- QUEJA
- RECLAMO
- SUGERENCIA
- DENUNCIA

**Nivel 5 — Causal RC6:**
Los causales están catalogados por series 100-700 según la migración 022:

| Serie | Categoría | Causales | SLA (días hábiles) |
|---|---|---|---|
| 100 | Calidad del Agua | 6 causales | 15 |
| 200 | Suspensión/Corte | 5 causales | 5 |
| 300 | Reconexión | 4 causales | 3 |
| 400 | Redes/Infraestructura | 7 causales | 15 |
| 500 | Nuevas Conexiones | 5 causales | 30 |
| 600 | Fraudes/Anomalías | 5 causales | 10 |
| 700 | Servicio/Atención | 9 causales | 15 |

### 11.2 Impacto en el Formulario de PQRS

El formulario actual (`templates/pqrs/nueva.html`) debe actualizarse para capturar los 5 niveles de forma secuencial (cascada). El comportamiento esperado:

1. Usuario selecciona Nivel 1 (Servicio) → carga Nivel 2
2. Usuario selecciona Nivel 2 (Tipo Solicitante) → habilita Nivel 3
3. Usuario selecciona Nivel 3 (Medio) → habilita Nivel 4
4. Usuario selecciona Nivel 4 (Tipo) → carga causales del Nivel 5 filtrados
5. Usuario selecciona Nivel 5 (Causal) → sistema calcula fecha límite de respuesta

### 11.3 SLA y Alertas Automáticas

El scheduler (APScheduler) ejecuta `tarea_diaria_completa` a las 06:00. Debe agregar:

- Verificación de PQRS próximas a vencer (≤2 días hábiles)
- Generación de notificación interna al responsable
- Para PQRS vencidas: alerta roja en dashboard

---

## PARTE 12 — CALIDAD DEL AGUA RC6.1

### 12.1 Parámetros Res. 2115/2007

El módulo `calidad_agua` (migración 023) tiene 11 parámetros base:

| Parámetro | Unidad | Valor Máximo | Frecuencia Mínima |
|---|---|---|---|
| pH | Unidades | 6.5-9.0 | Mensual |
| Cloro Residual | mg/L | 0.3-2.0 | Mensual |
| Turbiedad | UNT | 2 | Mensual |
| Color Aparente | UPC | 15 | Mensual |
| Conductividad | μS/cm | 1000 | Mensual |
| Olor | Umbral | 3 | Mensual |
| Sabor | Umbral | 3 | Mensual |
| Coliformes Totales | UFC/100mL | 0 | Mensual |
| E. coli | UFC/100mL | 0 | Mensual |
| Nitratos | mg/L | 10 | Mensual |
| Fluoruros | mg/L | 1.0 | Mensual |

### 12.2 Interfaz de Captura RC6.1

La interfaz de captura debe respetar la regla de simplicidad definida en RC6:

- Para cada parámetro: dropdown `ACEPTABLE / NO ACEPTABLE / NO MEDIDO`
- Si `NO ACEPTABLE`: aparece campo de valor observado + campo de acción correctiva
- No almacenar matrices complejas de análisis de laboratorio

### 12.3 Integración GIS

Cada muestra de agua debe estar vinculada a un `calidad_puntos_muestreo` que tiene coordenadas. La capa GIS de calidad del agua mostrará:

- Puntos de muestreo georreferenciados
- Color según último resultado: VERDE (todo aceptable), AMARILLO (sin medir), ROJO (algún parámetro no aceptable)

---

## PARTE 13 — PLAN DE MIGRACIONES RC6.1

### 13.1 Secuencia de Migraciones

| N° | Módulo | Archivo | Tablas | Dependencias |
|---|---|---|---|---|
| 026 | Suscriptores GC-01 | `026_suscriptores_gc01.py` | `gc_suscriptores`, `gc_conexiones` | 022 (áreas) |
| 027 | OT Materiales GA-07 | `027_ordenes_trabajo_rc6.py` | `ga_ot_materiales_utilizados`, `ga_ot_imagenes` | Base OT |
| 028 | Puntos Concertación GA-06 | `028_puntos_concertacion.py` | `ga_puntos_concertacion` | 022 (áreas) |
| 029 | Personal GL-01 | `029_personal_gl01.py` | `gl_personal` | `contactos` |
| 030 | Gobierno GE-01 | `030_gobierno_ge01.py` | `ge_actas`, `ge_resoluciones` | `registro_central` |

### 13.2 Reglas de Migración

Todas las migraciones RC6.1 deben:

1. Verificar existencia de tabla antes de `CREATE TABLE` (idempotencia)
2. Usar `CREATE INDEX IF NOT EXISTS`
3. Usar `PRAGMA foreign_keys=ON` dentro de la función `migrar()`
4. No realizar `DROP TABLE` ni `ALTER TABLE` destructivo
5. Para agregar columnas: verificar su existencia con `PRAGMA table_info()` antes de `ALTER TABLE ADD COLUMN`
6. Insertar datos semilla solo si la tabla está vacía

---

## PARTE 14 — RIESGOS Y MITIGACIÓN

### 14.1 Riesgos Técnicos

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Corrupción de migración (como RC5.5.12) | Media | Alto | Revisar cada archivo con `python -m py_compile` antes del commit |
| Duplicación de blueprints (proyectos v1 vs v2) | Alta | Medio | Desregistrar proy_bp en app.py antes de RC6.1 |
| Pérdida de datos al deprecar tablas | Media | Alto | Nunca DROP TABLE — solo deprecar con migración de datos |
| Lentitud en consultas GIS con múltiples capas | Media | Medio | Índices en coordenadas, paginación de GeoJSON |
| Conflicto de rutas entre blueprints fusionados | Alta | Alto | Revisión exhaustiva de `url_for()` en templates |

### 14.2 Riesgos Institucionales

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Nombre de cliente en código descubierto | Media | Alto | Grep automatizado en CI: `grep -r "ASUACAP\|cliente_nombre" routes/ templates/` |
| Cambio de numeración de causales PQRS | Baja | Medio | Catálogo en BD, no en código |
| Modificación de parámetros Res. 2115 | Baja | Medio | Parámetros en tabla `calidad_parametros`, configurables |
| Fallo de scheduler en PyInstaller | Media | Alto | Prueba de empaquetado después de cada RC |

### 14.3 Riesgos de Usabilidad

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Menú demasiado profundo con 5 áreas | Alta | Medio | Menú colapsable, breadcrumb, accesos rápidos en dashboard |
| Formulario PQRS con 5 niveles confuso | Media | Alto | Wizards paso a paso, indicador de progreso |
| Módulo suscriptores sin datos iniciales | Alta | Bajo | Script de migración de datos desde tabla `contactos` |

---

## PARTE 15 — CRONOGRAMA DE IMPLEMENTACIÓN

### 15.1 Fases de RC6.1

**FASE 1 — Limpieza y Consolidación (Semana 1)**
- Eliminar nombre de cliente del código (COMPLETADO en RC6.1 commit 6deb73f)
- Desregistrar blueprints legacy (proy_bp)
- Consolidar menú según estructura 5 áreas
- Pruebas de regresión en módulos congelados

**FASE 2 — GC-01 Suscriptores (Semana 2)**
- Migración 026
- Blueprint `suscriptores_bp`
- Template `suscriptores/panel.html`
- Integración GIS (capa de suscriptores)
- Vinculación con PQRS (campo `fk_suscriptor_id`)

**FASE 3 — GA-07 Órdenes de Trabajo (Semana 3)**
- Migración 027
- Blueprint `ordenes_trabajo_bp`
- Ciclo de vida: CREADA → ASIGNADA → EN EJECUCION → CERRADA
- Vinculación con inventarios (materiales usados)
- Acta de ejecución como documento GE-05

**FASE 4 — GA-06 Puntos de Concertación (Semana 4)**
- Migración 028
- Extensión `gis_bp` con nuevos endpoints
- Capa GIS de puntos de concertación
- Vinculación con GA-02 (Calidad del Agua)

**FASE 5 — GL-01 Personal y GE-01 Gobierno (Semana 5)**
- Migraciones 029 y 030
- Blueprint `laboral_bp` mínimo (directorio de personal)
- Blueprint `ge_bp` (actas, resoluciones)
- Actualización final del menú de navegación

**FASE 6 — Pruebas y Empaquetado (Semana 6)**
- Tests de volumen para módulos nuevos
- Prueba de empaquetado PyInstaller
- Backup de base de datos de producción piloto
- Documentación de API actualizada

### 15.2 Criterios de Aprobación por Fase

| Fase | Criterio de Aprobación |
|---|---|
| 1 | Grep de nombres de cliente retorna 0 resultados en routes/ y templates/ |
| 2 | GC-01: CRUD completo + 5 tests de volumen pasando |
| 3 | GA-07: Ciclo de vida completo + vinculación con inventarios funcionando |
| 4 | GA-06: Capa GIS visible + 3 puntos de prueba registrados |
| 5 | GL-01: Directorio funcional + GE-01: Acta de prueba generada |
| 6 | 0 errores en suite de tests existente + empaquetado PyInstaller exitoso |

---

## PARTE 16 — IMPACTO EN PERMISOS POR MÓDULO

### 16.1 Matriz de Acceso RC6.1

| Módulo | admin | presidente | tesorera | secretaria | auxiliar | tecnico |
|---|---|---|---|---|---|---|
| GE-01 Gobierno | ✔ | ✔ | — | ✔(R) | — | — |
| GE-05 Documentos | ✔ | ✔ | ✔(R) | ✔ | ✔(R) | ✔(R) |
| GC-01 Suscriptores | ✔ | ✔(R) | ✔(R) | ✔ | ✔(R) | — |
| GC-02 PQRS | ✔ | ✔ | — | ✔ | ✔(R) | — |
| GF-01 Presupuesto | ✔ | ✔ | ✔ | — | — | — |
| GF-02 Tesorería | ✔ | ✔(R) | ✔ | — | — | — |
| GF-05 Inventarios | ✔ | — | ✔ | ✔(R) | ✔ | ✔(R) |
| GF-06 Caja | ✔ | — | ✔ | — | — | — |
| GA-02 Calidad Agua | ✔ | ✔(R) | — | — | ✔ | ✔ |
| GA-03 Balance Hídrico | ✔ | ✔(R) | — | — | ✔ | ✔ |
| GA-07 OT | ✔ | ✔ | — | — | ✔ | ✔ |
| GA-08 Proyectos | ✔ | ✔ | ✔(R) | ✔(R) | ✔ | ✔ |
| GA-08 GIS | ✔ | ✔(R) | — | — | ✔(R) | ✔ |
| GL-01 Personal | ✔ | ✔ | ✔(R) | ✔(R) | — | — |
| Admin/Diagnóstico | ✔ | — | — | — | — | — |

**R = Solo lectura**

---

## PARTE 17 — GLOSARIO TÉCNICO

| Término | Definición |
|---|---|
| Acueducto comunitario | Sistema de abastecimiento de agua potable administrado por una organización sin ánimo de lucro, conformada por los propios usuarios del servicio |
| Blueprint | Componente modular de Flask que encapsula rutas, plantillas y recursos de un subdominio funcional |
| CAR | Corporación Autónoma Regional — entidad ambiental territorial que otorga concesiones de agua y supervisa vertimientos |
| CRA | Comisión de Regulación de Agua Potable y Saneamiento Básico — fija metodologías tarifarias |
| GIS | Geographic Information System — sistema de información geográfica para gestión de infraestructura |
| IANC | Índice de Agua No Contabilizada — diferencia entre agua producida y agua facturada, expresada en porcentaje |
| Idempotente | Propiedad de una migración que puede ejecutarse múltiples veces sin producir efectos secundarios |
| Macromedidor | Medidor instalado en la salida del sistema de tratamiento que cuantifica el volumen total de agua distribuida |
| Offline-first | Principio de diseño en que toda la funcionalidad está disponible sin conexión a Internet |
| OTP | One-Time Password — contraseña de un solo uso para autorización de documentos críticos |
| PTAP | Planta de Tratamiento de Agua Potable |
| PUEAA | Plan de Uso Eficiente y Ahorro del Agua — documento técnico exigido por Res. 330/2017 |
| PQRS | Petición, Queja, Reclamo, Sugerencia — mecanismo de participación ciudadana |
| PSMV | Plan de Saneamiento y Manejo de Vertimientos — exigido por las CARs |
| SLA | Service Level Agreement — plazo máximo de respuesta a una PQRS según Ley 1755/2015 |
| SPD | Servicios Públicos Domiciliarios — regulados por Ley 142/1994 |
| SSPD | Superintendencia de Servicios Públicos Domiciliarios — entidad de control y vigilancia |
| SUI | Sistema Único de Información — plataforma de reporte de datos al SSPD |
| TRD | Tabla de Retención Documental — instrumento archivístico que clasifica documentos y define tiempos de retención |
| UNT | Unidades Nefelométricas de Turbiedad — medida de turbidez del agua |
| WAL | Write-Ahead Log — modo de SQLite que permite lecturas concurrentes sin bloqueo de escritura |

---

## ESTADO DE APROBACIÓN

| Sección | Elaborado | Revisado | Aprobado |
|---|---|---|---|
| Parte 1 — Definición del Sistema | ✔ | Pendiente | Pendiente |
| Parte 2 — Mapa Actual | ✔ | Pendiente | Pendiente |
| Parte 3 — Diagnóstico por Área | ✔ | Pendiente | Pendiente |
| Parte 4 — Análisis de Brecha | ✔ | Pendiente | Pendiente |
| Parte 5 — Mapa Objetivo | ✔ | Pendiente | Pendiente |
| Parte 6 — Impacto Técnico | ✔ | Pendiente | Pendiente |
| Parte 7 — Impacto BD | ✔ | Pendiente | Pendiente |
| Parte 8 — Impacto Reportes | ✔ | Pendiente | Pendiente |
| Parte 9 — Impacto GIS | ✔ | Pendiente | Pendiente |
| Parte 10 — Impacto Documental | ✔ | Pendiente | Pendiente |
| Parte 11 — PQRS RC6.1 | ✔ | Pendiente | Pendiente |
| Parte 12 — Calidad del Agua | ✔ | Pendiente | Pendiente |
| Parte 13 — Plan de Migraciones | ✔ | Pendiente | Pendiente |
| Parte 14 — Riesgos | ✔ | Pendiente | Pendiente |
| Parte 15 — Cronograma | ✔ | Pendiente | Pendiente |
| Parte 16 — Permisos | ✔ | Pendiente | Pendiente |
| Parte 17 — Glosario | ✔ | Pendiente | Pendiente |

---

*Informe generado automáticamente por el sistema PARAGUASMJ — SIGCA RC6.1*  
*Fecha: 2026-06-13 | Commit de referencia: 6deb73f*  
*Próxima revisión: Al completar Fase 1 de implementación*
