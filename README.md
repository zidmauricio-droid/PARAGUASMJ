# PARAGUASMJ

**Sistema Institucional de Gestión para Acueductos Rurales de Colombia**

> Herramienta 100% gratuita, open source y offline-first para que los acueductos rurales colombianos cumplan con la normativa (Ley 142/1994, CRA, SSPD, CAR) y evolucionen en su gestión institucional.

**Acueducto piloto:** ASUACAP — Centro Poblado El Puente, Villeta, Cundinamarca.

---

## Arquitectura Institucional

PARAGUASMJ organiza toda su funcionalidad en cinco áreas de gestión institucional. Esta es la estructura canónica del sistema — cualquier nuevo módulo debe ubicarse dentro de una de estas áreas:

```
GE — Gestión Estratégica
GC — Gestión Comercial
GF — Gestión Financiera
GA — Gestión Ambiental y Operativa
GL — Gestión Laboral
```

---

## Módulos por Área

### GE — Gestión Estratégica

| Código | Módulo | Estado | Descripción |
|--------|--------|--------|-------------|
| GE-01 | Gobierno Corporativo | ✅ Activo | Actas, resoluciones, acuerdos, seguimiento de compromisos |
| GE-05 | Gestión Institucional | ✅ Activo | Reportes normativos CAR, SSPD, PUEAA, PEC |

> **Nota PEC:** El Plan de Emergencias y Contingencias NO es un módulo independiente. Existe únicamente como tipo de proyecto dentro de GA-08 Proyectos.

---

### GC — Gestión Comercial

| Código | Módulo | Estado | Descripción |
|--------|--------|--------|-------------|
| GC-01 | Suscriptores | ✅ Activo | Registro, estrato, macromedidor, historial, exportación SSPD |
| GC-02 | PQRS | ✅ Activo | Flujo completo Ley 142, vencimientos, exportación SUI/SSPD |
| GC-03 | Comunicaciones | ✅ Activo | Comunicaciones internas y externas, radicado, seguimiento |

---

### GF — Gestión Financiera

| Código | Módulo | Estado | Descripción |
|--------|--------|--------|-------------|
| GF-01 | Caja | ✅ Activo | Libro de caja menor, entradas y salidas diarias, exportación |
| GF-02 | Tesorería | ✅ Activo | Comprobantes de ingreso/egreso, estado de pago, aprobación |
| GF-03 | Bancos | ✅ Activo | Cuentas bancarias, movimientos, libro bancario |
| GF-04 | Presupuesto | ✅ Activo | Plan de cuentas, estructura presupuestal |
| GF-05 | Inventarios | ✅ Activo | Ítems, categorías, movimientos de entrada/salida, alertas de stock |
| GF-06 | Convenios | ✅ Activo | Contratos, adiciones, prórrogas, seguimiento de ejecución |

> GF no es un ERP de facturación. Es la gestión financiera básica de un acueducto comunitario rural.

---

### GA — Gestión Ambiental y Operativa

| Código | Módulo | Estado | Descripción |
|--------|--------|--------|-------------|
| GA-01 | GIS | ✅ Activo | Mapa Leaflet, infraestructura, fallas georreferenciadas, puntos de concertación, estado y fecha de certificación |
| GA-02 | Calidad del Agua | ✅ Activo | Resolución 2115/2007, parámetros configurables, resultado Aceptable/No Aceptable, valor encontrado, valor máx. permitido, observación, acción correctiva |
| GA-03 | Balance Hídrico | ✅ Activo | Lectura mensual macromedidor, producción, distribución, pérdidas, IANC, IUS CRA 906/2019, reportes FC01/FC15 SSPD |
| GA-04 | Captación | ✅ Activo | Fuentes de captación, caudal, tipo, coordenadas, estado, normativa ambiental |
| GA-07 | Órdenes de Trabajo | ✅ Activo | OT de mantenimiento, asignación, seguimiento, cierre |
| GA-08 | Proyectos | ✅ Activo | Gantt (Frappe), costos, evidencias SHA256, API REST — incluye proyectos tipo PEC, PSMV, PUEAA |

> **GA-03 Balance Hídrico:** Las lecturas son mensuales (macromedidor). No existen capturas diarias.
> **GA-04 Captación:** Antes denominada "Fuentes Hídricas". Renombrada en RC6.2.

---

### GL — Gestión Laboral

| Código | Módulo | Estado | Descripción |
|--------|--------|--------|-------------|
| GL-01 | Personal | ✅ Activo | Empleados, cargos, documentos laborales |

---

## Módulos Transversales

Estos módulos no pertenecen a un área específica — sirven a toda la organización:

| Módulo | Descripción |
|--------|-------------|
| Documentos | Editor TipTap, 44 tipos, plantillas institucionales, PDF con membrete, firmas OTP |
| Auditoría | Log de accesos, diagnósticos del sistema, gestión de usuarios |
| Configuración | Datos de la organización, logo, colores institucionales |

---

## Stack Tecnológico

| Capa | Tecnología | Licencia |
|------|-----------|---------|
| Backend | Flask 3.1 + Waitress | BSD |
| Base de datos | SQLite 3 WAL | Dominio público |
| Frontend | Bootstrap 5.3 + Jinja2 | MIT |
| Editor | TipTap 2.4 UMD | MIT |
| Mapas | Leaflet 1.9 | BSD |
| PDF | ReportLab 4.1 | BSD |
| Excel | OpenPyXL 3.1 | MIT |
| Gantt | Frappe Gantt | MIT |
| IA (opcional) | Claude (Anthropic) | — |

---

## Normativa Colombiana Implementada

| Norma | Aplicación |
|-------|-----------|
| Ley 142 de 1994 | Servicios Públicos Domiciliarios — PQRS, suscriptores |
| Resolución CRA 906/2019 | IUS — Índice Único de Servicio |
| Resolución 2115 de 2007 | Calidad del agua para consumo humano |
| Resolución 330/2017 | Reglamento técnico del sector de agua potable |
| Ley 373/1997 | PUEAA — Plan de Uso Eficiente del Agua |
| Resolución SSPD 54575/2015 | PQRS en servicios públicos |

---

## Instalación

### Windows (producción)

```bash
# 1. Descomprimir PARAGUASMJ_RC6.zip
# 2. Doble clic en INSTALAR.bat
# 3. Doble clic en INICIAR.bat
# 4. Abrir http://127.0.0.1:5000
# Credenciales iniciales: admin / PARAGUASMJ2026
```

### Desarrollo

```bash
git clone https://github.com/TU_USUARIO/PARAGUASMJ.git
cd PARAGUASMJ
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

### Variables de entorno

```bash
SECRET_KEY=clave_aleatoria_segura
ANTHROPIC_API_KEY=opcional_para_IA
```

---

## Estructura del Proyecto

```
PARAGUASMJ/
├── app.py                  # Fábrica Flask — registro de blueprints
├── config.py               # Configuración central
├── run.py                  # Punto de entrada (Waitress)
├── routes/                 # Blueprints por módulo institucional
│   ├── gobierno.py         # GE-01
│   ├── reportes_normativos.py  # GE-05
│   ├── suscriptores.py     # GC-01
│   ├── pqrs.py             # GC-02
│   ├── comunicaciones.py   # GC-03
│   ├── finanzas.py         # GF-01..04
│   ├── inventarios.py      # GF-05
│   ├── convenios.py        # GF-06
│   ├── gis.py              # GA-01
│   ├── calidad_agua.py     # GA-02
│   ├── balance_hidrico.py  # GA-03 + GA-04
│   ├── ordenes_trabajo.py  # GA-07
│   ├── proyectos2.py       # GA-08
│   ├── laboral.py          # GL-01
│   ├── documentos.py       # Transversal
│   └── auditoria.py        # Transversal
├── core/                   # Servicios internos (PDF, email, OTP, backup)
├── templates/              # Jinja2 — un subdirectorio por módulo
├── static/
│   ├── css/estilo.css      # Tema institucional oscuro
│   └── vendor/bootstrap/   # Bootstrap 5.3.2 local (sin CDN)
└── database/
    └── inicializar_db.py   # Esquema SQLite + migraciones
```

---

## Principios de Desarrollo

- **Sin CDN.** Todos los assets son locales (`static/vendor/`). El sistema debe funcionar sin internet.
- **Sin colores hardcodeados.** El tema visual usa variables CSS (`var(--bg-card)`, `var(--color-success)`, etc.).
- **Sin módulos paralelos.** Cada funcionalidad tiene un solo lugar en la arquitectura GE/GC/GF/GA/GL.
- **Sin código heredado.** Si algo ya no es válido en la arquitectura actual, se elimina completamente.
- **Normalidad hídrica.** El sistema modela un acueducto rural típico — no un ERP, no un sistema bancario.

---

## Licencia

MIT — Libre para uso, modificación y distribución.

*Hecho para los acueductos comunitarios de Colombia.*
