# PARAGUASMJ RC6 — ARQUITECTURA FUNCIONAL Y DOCUMENTAL
## Documento Maestro de Arquitectura — Versión Aprobación Pre-Desarrollo

**Estado:** Pendiente de aprobación institucional  
**Versión:** RC6.1  
**Fecha:** 2026-06-13  
**Clasificación:** GE-05 Gestión Documental — Documento Técnico Institucional

---

# PARTE 1 — PRINCIPIOS FUNDACIONALES

## 1.1 Definición del Sistema

PARAGUASMJ NO es un software de facturación.

PARAGUASMJ ES:

> **Sistema Integral de Gestión Documental, Operativa y Administrativa para Acueductos Comunitarios de Colombia.**

Alcance exclusivo:
- Control documental institucional
- Control operativo del acueducto
- Gestión de suscriptores y PQRS
- Calidad del agua (Res. 2115/2007)
- Balance hídrico y macromedición
- GIS operacional
- Inventarios de materiales y activos
- Proyectos institucionales
- Finanzas básicas (caja, bancos, tesorería)
- Gestión de personal y SST

Fuera del alcance (prohibido implementar):
- Facturación masiva
- Ciclo comercial tipo ERP
- Tarifas y liquidación de consumos
- Lecturas diarias de micromedidores para facturación
- CRM comercial

---

# PARTE 2 — ESTRUCTURA INSTITUCIONAL

## 2.1 Cinco Áreas Maestras

```
┌─────────────────────────────────────────────────────┐
│              PARAGUASMJ RC6                         │
│       Arquitectura Institucional por Áreas          │
├──────┬──────┬──────┬──────┬──────────────────────────┤
│  GE  │  GC  │  GF  │  GA  │  GL                     │
└──────┴──────┴──────┴──────┴──────────────────────────┘
```

## 2.2 Subáreas Oficiales

### GE — Gestión Estratégica
| Código | Nombre |
|--------|--------|
| GE-01 | Gobierno Corporativo |
| GE-02 | Planeación |
| GE-03 | Control Interno |
| GE-04 | Jurídica |
| GE-05 | Gestión Documental |

### GC — Gestión Comercial
| Código | Nombre |
|--------|--------|
| GC-01 | Suscriptores |
| GC-02 | PQRS |
| GC-03 | Cartera |
| GC-04 | Conexiones |
| GC-05 | Fraudes |

### GF — Gestión Financiera
| Código | Nombre |
|--------|--------|
| GF-01 | Presupuesto |
| GF-02 | Tesorería |
| GF-03 | Contabilidad |
| GF-04 | Contratación |
| GF-05 | Inventarios |
| GF-06 | Caja |

### GA — Gestión Ambiental y Operativa
| Código | Nombre |
|--------|--------|
| GA-01 | Operación Acueducto |
| GA-02 | Calidad del Agua |
| GA-03 | Balance Hídrico |
| GA-04 | Infraestructura |
| GA-05 | Mantenimiento |
| GA-06 | Cuenca Hidrográfica |
| GA-07 | Órdenes de Trabajo |
| GA-08 | GIS |
| GA-09 | Proyectos |

### GL — Gestión Laboral
| Código | Nombre |
|--------|--------|
| GL-01 | Personal |
| GL-02 | Selección |
| GL-03 | Evaluación |
| GL-04 | Capacitación |
| GL-05 | SST |

---

# PARTE 3 — GIS COMO NÚCLEO OPERATIVO

## 3.1 Principio Rector

El GIS (GA-08) es la fuente primaria de información operacional.
Todo elemento físico del sistema de acueducto debe existir georreferenciado en el GIS.

## 3.2 Capas GIS Obligatorias

```
CAPA 1 — INFRAESTRUCTURA HÍDRICA
  ├── Bocatoma
  ├── Desarenador
  ├── PTAP
  ├── Tanques de almacenamiento
  ├── Red de distribución (trazado)
  ├── Válvulas (cierre, control, aire, regulación)
  ├── Hidrantes
  └── Macromedidores

CAPA 2 — SUSCRIPTORES Y PREDIOS
  ├── Predios (polígono o punto)
  ├── Acometidas domiciliarias
  ├── Micromedidores (punto)
  └── Suscriptores activos / inactivos

CAPA 3 — OPERATIVA
  ├── Órdenes de Trabajo (punto georreferenciado)
  ├── Daños y fallas reportadas
  ├── Mantenimientos ejecutados
  └── Lecturas de macromedidor (punto)

CAPA 4 — AMBIENTAL
  ├── Cuenca hidrográfica (polígono)
  ├── Puntos de concertación ambiental
  ├── Nivel de quebrada (punto + escala)
  └── Puntos de muestreo de calidad de agua

CAPA 5 — PROYECTOS
  ├── Área de influencia del proyecto
  ├── Obra georreferenciada
  └── Avance físico sobre mapa
```

## 3.3 Relaciones GIS → Módulos

| Módulo | Dato que toma del GIS |
|--------|-----------------------|
| GA-01 Operación | Estado red, válvulas, tanques |
| GA-02 Calidad Agua | Puntos de muestreo georreferenciados |
| GA-03 Balance Hídrico | Macromedidor, bocatoma |
| GA-07 Órdenes Trabajo | Localización exacta del daño |
| GA-09 Proyectos | Área de la obra |
| GC-01 Suscriptores | Predio, acometida, micromedidor |
| GC-04 Conexiones | Trazado de nueva acometida |

---

# PARTE 4 — ARQUITECTURA POR MÓDULO

## 4.1 GC-01 Suscriptores

**Entidad:** Persona natural o jurídica vinculada contractualmente al servicio.

**Datos obligatorios:**
- Código único de suscriptor
- Identificación (NIT/CC)
- Nombre completo / Razón social
- Predio (vinculado al GIS)
- Estrato (1-6)
- Tipo de uso (residencial / comercial / industrial / oficial)
- Estado del servicio (activo / suspendido / cortado / inactivo)
- Fecha de afiliación
- Micromedidor asignado (código, marca, fecha instalación)
- Acometida (diámetro, material, estado)

**Diferencia Suscriptor vs Usuario:**
- **Suscriptor** = Afiliado registrado contractualmente
- **Usuario** = Cualquier persona que recibe o solicita el servicio (no necesariamente afiliado)

## 4.2 GC-02 PQRS — Nueva Estructura Obligatoria

### Jerarquía de Clasificación (5 niveles)

```
NIVEL 1 — SERVICIO
│
├── ACUEDUCTO
│
└── ALCANTARILLADO

NIVEL 2 — SOLICITANTE
│
├── Suscriptor (vinculado al registro de suscriptores)
├── Usuario (persona natural no registrada)
└── Entidad (pública, privada, veeduría, JAC, contratista)

NIVEL 3 — CANAL DE RECEPCIÓN
│
├── 01 Presencial / Ventanilla
├── 02 Correo electrónico
├── 03 WhatsApp
├── 04 Teléfono
├── 05 Oficio / Correo físico
├── 06 Página Web
└── 99 Otro

NIVEL 4 — TIPO DE PQRS
│
├── Petición
├── Queja
├── Reclamo
├── Solicitud
├── Denuncia
├── Sugerencia
└── Felicitación

NIVEL 5 — CAUSAL (código + nombre)
│
└── [Ver catálogo completo Sección 4.2.1]
```

### 4.2.1 Catálogo Maestro de Causales RC6

```
SERIE 100 — CALIDAD DEL AGUA
  101  Agua con color anormal                    SLA: 5 días
  102  Agua con olor anormal                     SLA: 5 días
  103  Agua con sabor anormal                    SLA: 5 días
  104  Agua turbia                               SLA: 3 días
  105  Presencia de partículas o sedimentos      SLA: 3 días
  106  Resultado de laboratorio no conforme      SLA: 5 días
  107  Posible contaminación del sistema         SLA: 2 días
  108  Baja desinfección (cloro insuficiente)    SLA: 3 días

SERIE 200 — SUSPENSIÓN DEL SERVICIO
  201  Suspensión sin aviso previo               SLA: 5 días
  202  Suspensión injustificada                  SLA: 5 días
  203  Negativa a suspender servicio solicitada  SLA: 5 días
  204  Suspensión en dirección errónea           SLA: 5 días
  205  Corte por error administrativo            SLA: 3 días

SERIE 300 — RECONEXIÓN
  301  Retraso en la reconexión                  SLA: 3 días
  302  Cobro por reconexión en disputa           SLA: 10 días
  303  Reconexión incompleta o deficiente        SLA: 3 días
  304  Reconexión no realizada                   SLA: 2 días

SERIE 400 — REDES E INFRAESTRUCTURA
  401  Fuga en red principal                     SLA: 2 días
  402  Fuga en acometida domiciliaria            SLA: 3 días
  403  Daño en tubería                           SLA: 3 días
  404  Daño en válvula                           SLA: 5 días
  405  Daño en hidrante                          SLA: 5 días
  406  Rebose de alcantarillado                  SLA: 2 días
  407  Obstrucción de alcantarillado             SLA: 3 días
  408  Colapso de red                            SLA: 1 día
  409  Falta de mantenimiento preventivo         SLA: 10 días

SERIE 500 — CONEXIONES
  501  Solicitud de nueva conexión               SLA: 15 días
  502  Modificación de conexión existente        SLA: 10 días
  503  Traslado de acometida                     SLA: 10 días
  504  Viabilidad de servicio                    SLA: 15 días
  505  Independización de acometida              SLA: 15 días

SERIE 600 — FRAUDES Y ANORMALIDADES
  601  Investigación por fraude                  SLA: 10 días
  602  Manipulación de medidor                   SLA: 5 días
  603  Conexión clandestina / ilegal             SLA: 5 días
  604  Revisión de acometida por anomalía        SLA: 5 días
  605  Recuperación de consumos no medidos       SLA: 10 días
  606  Normalización del servicio post-fraude    SLA: 5 días

SERIE 700 — SERVICIO Y DISPONIBILIDAD
  701  Intermitencia del servicio                SLA: 5 días
  702  Falta total del servicio                  SLA: 3 días
  703  Continuidad deficiente                    SLA: 5 días
  704  Baja disponibilidad horaria               SLA: 5 días
  705  Cobertura insuficiente del servicio       SLA: 10 días
```

**Campo SLA:** Días hábiles según Ley 1755/2015 y festivos colombianos.

## 4.3 GA-02 Calidad del Agua

**Principio:** No es un módulo de adjuntos PDF. Es un módulo técnico estructurado.

### Estructura de Captura

```
MUESTRA
│
├── Código único (CA-AAAA-NNNN)
├── Fecha de toma
├── Punto de muestreo (vinculado GIS)
├── Laboratorio
├── Responsable
└── Estado: registrada | completa | con_alerta

PARÁMETROS (Res. 2115/2007 — Mínimo)
│
├── pH             (6.5 – 9.0)
├── Cloro Residual (0.3 – 2.0 mg/L)
├── Turbiedad      (0 – 2 UNT)
├── Color Aparente (0 – 15 UPC)
├── Conductividad  (0 – 1000 µS/cm)
├── Olor           (Aceptable / No Aceptable)
├── Sabor          (Aceptable / No Aceptable)
├── Coliformes Totales (0 UFC/100mL)
├── E. coli        (0 UFC/100mL)
├── Nitratos       (0 – 10 mg/L)
└── Fluoruros      (0 – 1.0 mg/L)

RESULTADO POR PARÁMETRO
│
├── ACEPTABLE
├── NO_ACEPTABLE → habilita:
│   ├── Valor obtenido
│   ├── Límite normativo
│   ├── Observación
│   └── Acción correctiva
└── NO_MEDIDO
```

### Clasificación Documental
- Por: Año / Mes / Punto de Muestreo
- Código: CA-{AÑO}-{CONSECUTIVO}
- Área: GA-02
- Sin carpetas manuales

## 4.4 GA-03 Balance Hídrico

**Principio:** Solo lecturas mensuales. Fuente: macromedidor.

### Variables Obligatorias

```
MACROMEDIDOR MENSUAL
│
├── Año
├── Mes
├── Fecha de lectura
├── Lectura inicial (m³)
├── Lectura final (m³)
└── Volumen producido (calculado = final - inicial)

NIVEL DE QUEBRADA MENSUAL
│
├── Año
├── Mes
├── Fecha de lectura
├── Nivel (cm) — libre o rangos 0,20,40...200
└── Observaciones

RESUMEN MENSUAL (calculado)
│
├── Volumen producido (m³)
├── Volumen facturado/distribuido (m³)
├── Pérdidas (m³)
├── IANC (%)
└── Suscriptores activos
```

## 4.5 GA-09 Proyectos

**Principio:** Un único módulo PROYECTOS. No existen módulos PUEAA, PSMV, PEC, etc.

### Estructura Universal de Proyecto

```
PROYECTO
│
├── IDENTIFICACIÓN
│   ├── Código (PRY-AAAA-NNN)
│   ├── Nombre (libre — "PUEAA 2026-2031", "Tanque 240m3", etc.)
│   ├── Tipo (configurable por el cliente)
│   ├── Fecha inicio
│   ├── Fecha fin
│   └── Duración (1 a 30 años, meses, días)
│
├── METAS E INDICADORES
│   ├── Meta (texto + indicador cuantitativo)
│   ├── Unidad de medida
│   ├── Valor esperado
│   ├── Valor ejecutado
│   └── % avance
│
├── ACTIVIDADES
│   ├── Código actividad
│   ├── Responsable
│   ├── Fecha programada
│   ├── Fecha ejecutada
│   └── Estado
│
├── PRESUPUESTO
│   ├── Rubro
│   ├── Valor programado
│   └── Valor ejecutado
│
├── DOCUMENTACIÓN
│   ├── Contratos
│   ├── Convenios
│   ├── Actas
│   ├── Informes de avance
│   └── Evidencias fotográficas
│
└── GEORREFERENCIACIÓN (GIS)
    └── Área del proyecto en mapa
```

## 4.6 GF-05 Inventarios

**Principio:** Módulo independiente. No mezclado con Tesorería.

### Categorías
- Materiales de construcción
- Equipos
- Herramientas
- Químicos / Reactivos
- Activos fijos
- EPP (Elementos de Protección Personal)
- Otros

### Flujo
```
ITEM → ENTRADA (compra/donación) → EXISTENCIA
              ↓
         SALIDA (uso/OT/obra) → REGISTRA BAJA
              ↓
         TRASLADO (entre áreas)
              ↓
         AJUSTE (inventario físico)
              ↓
         BAJA DEFINITIVA
```

### Relaciones
- GF-04 Contratación → genera Entrada al inventario
- GA-07 Órdenes de Trabajo → consume materiales del inventario
- GF-02 Tesorería → registra el pago (no la entrada de inventario)
- GL-05 SST → consume EPP del inventario

---

# PARTE 5 — ARQUITECTURA DOCUMENTAL

## 5.1 Estructura Física de Almacenamiento

```
REPOSITORIO PARAGUASMJ/
│
├── GE/
│   ├── GE-01_Gobierno_Corporativo/
│   ├── GE-02_Planeacion/
│   ├── GE-03_Control_Interno/
│   ├── GE-04_Juridica/
│   └── GE-05_Gestion_Documental/
│
├── GC/
│   ├── GC-01_Suscriptores/
│   ├── GC-02_PQRS/
│   ├── GC-03_Cartera/
│   ├── GC-04_Conexiones/
│   └── GC-05_Fraudes/
│
├── GF/
│   ├── GF-01_Presupuesto/
│   ├── GF-02_Tesoreria/
│   ├── GF-03_Contabilidad/
│   ├── GF-04_Contratacion/
│   ├── GF-05_Inventarios/
│   └── GF-06_Caja/
│
├── GA/
│   ├── GA-01_Operacion/
│   ├── GA-02_Calidad_Agua/
│   │   └── {AAAA}/{MM}/{codigo_muestra}/
│   ├── GA-03_Balance_Hidrico/
│   │   └── {AAAA}/{MM}/
│   ├── GA-04_Infraestructura/
│   ├── GA-05_Mantenimiento/
│   ├── GA-06_Cuenca/
│   ├── GA-07_Ordenes_Trabajo/
│   │   └── {AAAA}/{codigo_OT}/
│   ├── GA-08_GIS/
│   │   ├── Planos_PDF/
│   │   ├── Planos_DWG/
│   │   └── Capas_SHP_GeoJSON/
│   └── GA-09_Proyectos/
│       └── {codigo_proyecto}/
│
└── GL/
    ├── GL-01_Personal/
    ├── GL-02_Seleccion/
    ├── GL-03_Evaluacion/
    ├── GL-04_Capacitacion/
    └── GL-05_SST/
```

## 5.2 Convención de Nombres Documentales

```
Formato: {AREA}-{SUBAREA}-{TIPO}-{AAAA}-{CONSECUTIVO}

Ejemplos:
  GE-05-RES-2026-0001  → Resolución 001 de 2026 (Gestión Documental)
  GC-02-PQR-2026-0247  → PQRS 247 de 2026 (Comercial)
  GF-04-CTR-2026-0012  → Contrato 012 de 2026 (Contratación)
  GA-02-CA-2026-0034   → Muestra de calidad agua 034 de 2026
  GA-07-OT-2026-0089   → Orden de Trabajo 089 de 2026
  GA-09-PRY-2026-0003  → Proyecto 003 de 2026
```

## 5.3 Metadatos Obligatorios por Documento

Todos los documentos deben registrar:

| Campo | Descripción |
|-------|-------------|
| UUID | Identificador único universal (inmutable) |
| Código | Código institucional según convención |
| Área | GE / GC / GF / GA / GL |
| Subárea | GE-01 ... GL-05 |
| Tipo documental | Según tabla TRD |
| Serie TRD | Código de serie archivística |
| Subserie TRD | Código de subserie |
| Fecha radicación | Fecha de ingreso al sistema |
| Estado | Borrador / En revisión / Aprobado / Archivado |
| Versión | Número de versión |
| Creado por | Usuario del sistema |
| Identity Hash | Hash SHA-256 del contenido (inmutable) |
| Chain Fingerprint | Cadena de verificación OAIS |
| Expediente | Código del expediente relacionado |
| Retención gestión | Años en archivo de gestión (TRD) |
| Retención central | Años en archivo central (TRD) |
| Disposición final | Conservación / Eliminación / Digitalización |

## 5.4 Flujo Documental

```
RADICACIÓN
    │
    ▼
CLASIFICACIÓN AUTOMÁTICA (Reglas TRD)
    │ ← tipo_documento + asunto → serie + subserie + retención
    ▼
ASIGNACIÓN DE CÓDIGO
    │ ← área + tipo + año + consecutivo
    ▼
EXPEDIENTE
    │ ← agrupación lógica por asunto, proyecto o suscriptor
    ▼
TRAMITACIÓN / EDICIÓN
    │ ← versionamiento, firmas, aprobaciones
    ▼
APROBACIÓN / CIERRE
    │ ← estado = "Aprobado" → inmutable (WORM)
    ▼
ARCHIVO DE GESTIÓN
    │ ← retención según TRD
    ▼
TRANSFERENCIA ARCHIVO CENTRAL
    │ ← hoja de control, índice, acta de transferencia
    ▼
DISPOSICIÓN FINAL
    │ ← conservación total o eliminación documentada
    ▼
ARCHIVO HISTÓRICO / BAJA DOCUMENTAL
```

---

# PARTE 6 — DIAGRAMA DE DEPENDENCIAS ENTRE MÓDULOS

```
┌─────────────────────────────────────────────────────────────────┐
│                    GA-08 GIS (NÚCLEO CENTRAL)                   │
│  Fuente de verdad para: ubicación, red, infraestructura, predios│
└────────┬────────┬───────┬────────┬────────┬──────────────────────┘
         │        │       │        │        │
    ┌────▼──┐ ┌───▼──┐ ┌──▼───┐ ┌─▼────┐ ┌─▼────────┐
    │GA-01  │ │GA-02 │ │GA-03 │ │GA-07 │ │GC-01     │
    │Operac.│ │Cal.  │ │Bal.  │ │OT    │ │Suscript. │
    │Acued. │ │Agua  │ │Hídr. │ │      │ │          │
    └───┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └────┬─────┘
        │        │        │        │           │
        │        │        │        │        ┌──▼────┐
        │        │   ┌────▼──┐  ┌──▼────┐   │GC-02  │
        │        │   │Reporte│  │GF-05  │   │PQRS   │
        │        │   │CRA    │  │Invent.│   └───────┘
        │        │   │SSPD   │  └───────┘
        │        │   └───────┘
        │     ┌──▼────────────────────────────┐
        │     │  GA-09 PROYECTOS              │
        │     │  (Universal: PUEAA/PSMV/obras)│
        │     └───────────────────────────────┘
        │
    ┌───▼───────────────────────────────────────────┐
    │  GE-05 GESTIÓN DOCUMENTAL                     │
    │  Registro Central + Expedientes + TRD + OAIS  │
    └────────────────────────────────────────────────┘

FINANZAS (GF):
  GF-06 Caja ←──→ GF-02 Tesorería ←──→ GF-04 Contratación
                                              │
                                         GF-05 Inventarios
                                              │
                                         GA-07 Órdenes Trabajo
```

---

# PARTE 7 — MAPA DE MIGRACIÓN DE MÓDULOS EXISTENTES

| Módulo Actual | Área RC6 | Subárea RC6 | Acción |
|---------------|----------|-------------|--------|
| `registro_central` | GE | GE-05 | Migrar + reclasificar áreas |
| `pqrs` | GC | GC-02 | Migrar + nuevas causales 100-700 |
| `proyectos` (v1) | GA | GA-09 | Fusionar con proyectos_v2 |
| `proyectos_v2` | GA | GA-09 | Módulo definitivo |
| `balance_hidrico` | GA | GA-03 | Mantener + nueva tabla mensual |
| `gis_infraestructura` | GA | GA-08 | Ampliar capas |
| `finanzas_caja` | GF | GF-06 | Mantener como GF-06 Caja |
| `bancos/movimientos` | GF | GF-02 | Mantener como GF-02 Tesorería |
| `expedientes` | GE | GE-05 | Mantener |
| `contactos` | GC | GC-01 | Migrar a suscriptores_registro |
| `comunicaciones` | GE | GE-04 | Mantener como Jurídica/Correspondencia |
| `convenios` | GF | GF-04 | Mantener como Contratación |
| `emergencias` | GA | GA-01 | Mantener como Operación |
| `calidad_agua` (RC6) | GA | GA-02 | NUEVO — ya creado |
| `inventarios` (RC6) | GF | GF-05 | NUEVO — ya creado |
| `laboral` | GL | GL-01..05 | PENDIENTE — crear |
| `suscriptores` | GC | GC-01 | PENDIENTE — crear CRUD |
| `ordenes_trabajo` | GA | GA-07 | Parcial en PQRS — ampliar |

---

# PARTE 8 — LISTA DE ARCHIVOS A CREAR/MODIFICAR

## Archivos a Crear (Fase RC6.1)

### Routes (Nuevos)
- `routes/suscriptores.py` — GC-01 CRUD suscriptores
- `routes/laboral.py` — GL-01..05 Personal, Selección, Evaluación, SST
- `routes/ordenes_trabajo_rc6.py` — GA-07 ciclo completo OT

### Templates (Nuevos)
- `templates/suscriptores/panel.html`
- `templates/laboral/panel.html`
- `templates/ordenes_trabajo/panel.html`

### Migraciones (Pendientes)
- `025_suscriptores_crud.py` — Tabla suscriptores con todos los campos
- `026_laboral_personal.py` — Personal, SST, capacitaciones
- `027_ordenes_trabajo_rc6.py` — OT ciclo completo con materiales
- `028_gis_capas_ampliadas.py` — Nuevas capas GIS

## Archivos a Modificar (Fase RC6.1)

| Archivo | Cambio |
|---------|--------|
| `routes/pqrs.py` | Causales 100-700, nuevo formulario 5 niveles |
| `templates/pqrs/nueva.html` | Formulario con jerarquía servicio/solicitante/canal |
| `routes/proyectos_v2.py` | Fusionar con proyectos v1, unificar |
| `routes/gis.py` | Agregar capas de cuenca, concertación |
| `templates/base.html` | Navbar estructurada por áreas GE/GC/GF/GA/GL |
| `database/inicializar_db.py` | Seed de áreas, causales, parámetros calidad agua |

---

# PARTE 9 — RIESGOS DE MIGRACIÓN

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Pérdida datos PQRS al cambiar causales | Alto | Migration idempotente, mapeo old→new |
| Ruptura de URL existentes en proyectos v1/v2 | Medio | Mantener rutas antiguas como alias |
| Reclasificación de área en `registro_central` | Medio | Script de mapeo automático |
| Contactos sin suscriptor_registro | Bajo | Migración opcional, FK nullable |
| Módulo `proyectos` v1 con datos históricos | Alto | Fusionar → tabla única con flag versión |

---

# PARTE 10 — ESTADO DE APROBACIÓN

| Sección | Estado |
|---------|--------|
| 5 Áreas institucionales | ⬜ Pendiente aprobación |
| 29 Subáreas | ⬜ Pendiente aprobación |
| Catálogo PQRS 100-700 (41 causales) | ⬜ Pendiente aprobación |
| Estructura Calidad Agua | ⬜ Pendiente aprobación |
| Balance Hídrico mensual | ⬜ Pendiente aprobación |
| Módulo Proyectos universal | ⬜ Pendiente aprobación |
| Estructura documental + metadatos | ⬜ Pendiente aprobación |
| Mapa de migración | ⬜ Pendiente aprobación |

**Cuando esta arquitectura sea aprobada, se inicia la fase de desarrollo RC6.1.**

---

*Documento generado por: PARAGUASMJ Architecture Engine RC6*  
*Herramientas utilizadas: Claude Sonnet 4.6 + Canva Report + Canva Poster*  
*Diseños Canva disponibles en:*  
- *Reporte: https://www.canva.com/d/QYboqCvQdOKTfwn*  
- *Póster de áreas: https://www.canva.com/d/dO3P2iucxSYKZc2*
