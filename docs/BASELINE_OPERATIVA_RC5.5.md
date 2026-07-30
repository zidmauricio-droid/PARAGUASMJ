# BASELINE OPERATIVA RC5.5 — PARAGUASMJ SIGCA
**Versión:** RC5.5 · Fecha de congelamiento: 2026-06-12  
**Responsable técnico:** Equipo SIGCA · ASUACAP — Villeta, Cundinamarca

---

## 1. Propósito

Este documento define qué componentes del sistema PARAGUASMJ están **congelados** (no pueden modificarse sin proceso formal), cuáles pueden **evolucionar controladamente**, y cuáles son **extensiones opcionales**.

Su objetivo es garantizar que RC5.5 sea estable, auditable y reproducible durante el periodo de soporte LTS.

---

## 2. Niveles de Módulos

### NIVEL 1 — NÚCLEO INSTITUCIONAL (CONGELADO)

> Nunca debe romperse. Cualquier modificación requiere nuevo número de versión mayor.

| Módulo | Archivo principal | Razón |
|--------|------------------|-------|
| Autenticación | `routes/autenticacion.py` | Control de acceso crítico |
| Documentos / Registro Central | `routes/documentos.py` | Trazabilidad documental |
| Expedientes | `routes/expedientes.py` | Custodia legal |
| Auditoría | `routes/auditoria.py`, `utils/audit.py` | Trazabilidad de acciones |
| Backups | `core/backup_manager.py` | Recuperación ante desastres |
| CSRF | `core/csrf_manager.py` | Seguridad transaccional |
| OTP | `core/otp_manager.py` | Autorización de documentos |
| Base de datos | `core/database_manager.py`, `database/inicializar_db.py` | Integridad de datos |
| Configuración | `config.py` | Parámetros del sistema |

**Regla:** Un error en estos módulos debe corregirse en un parche `RC5.5.x`. No se agregan funcionalidades.

---

### NIVEL 2 — OPERACIÓN (PUEDE EVOLUCIONAR CONTROLADAMENTE)

> Puede recibir mejoras menores sin romper compatibilidad.

| Módulo | Archivo principal |
|--------|------------------|
| PQRS | `routes/pqrs.py` |
| Finanzas | `routes/finanzas.py` |
| Convenios | `routes/convenios.py` |
| Emergencias | `routes/emergencias.py` |
| Reportes normativos | `routes/reportes_normativos.py` |
| Balance Hídrico | `routes/balance_hidrico.py` |
| Comunicaciones | `routes/comunicaciones.py` |
| Proyectos | `routes/proyectos_v2.py` |

**Regla:** Los cambios deben ser retrocompatibles. Nuevas columnas con `DEFAULT NULL`. No romper APIs existentes.

---

### NIVEL 3 — EXTENSIONES (OPCIONALES, RC6.0+)

> No forman parte del núcleo. Pueden activarse/desactivarse sin afectar Nivel 1.

| Extensión | Estado |
|-----------|--------|
| IA / Análisis predictivo | Planificado RC6.0 |
| Multi-tenant completo | Planificado RC6.0 |
| Sincronización cloud | No planificado |
| Blockchain / TSA externo | No planificado |
| OCR avanzado | No planificado |
| GIS avanzado | No planificado |
| Microservicios | No planificado |

---

## 3. Qué SÍ puede cambiar (sin afectar baseline)

- Textos de interfaz (labels, mensajes)
- Logos e imágenes institucionales
- Configuraciones en tabla `configuracion`
- Plantillas de reportes Excel/PDF
- Umbrales (días de alerta, límites de vencimiento)
- Datos semilla / configuraciones iniciales

---

## 4. Qué NO puede cambiar sin proceso formal

| Componente | Razón |
|-----------|-------|
| Clave primaria `pk_*` de tablas | Rompería integridad referencial |
| Estructura de `audit_log` | Trazabilidad legal |
| Estructura de `registro_central` | Custodia documental |
| Algoritmo de generación OTP | Seguridad de firmantes |
| Clave de sesión CSRF (`csrf_token`) | Compatibilidad entre módulos |
| Prefijo de backup (`paraguasmj_*.db`) | Scripts de restauración |
| `BASELINE_ID = "PARAGUASMJ-RC5.5"` | Identificación institucional |
| Columnas `COLS_PERMITIDAS` en balance hídrico | Integridad de datos RAS |

---

## 5. Proceso formal para modificar Nivel 1

1. Crear ADR en `docs/ADR/ADR-XXX-descripcion.md`
2. Aprobar en reunión de comité técnico
3. Crear rama `fix/RC5.5.x-descripcion`
4. Revisar que no rompa tests existentes
5. Actualizar `ARCHITECTURE_MANIFEST.yaml`
6. Actualizar este documento si aplica
7. Generar nuevo ZIP con nombre `PARAGUASMJ_SIGCA_RC5.5.x_YYYYMMDD.zip`

---

## 6. Ciclo de vida RC5.5

```
RC5.5.0  (2026-06-12) — Baseline institucional congelada
RC5.5.1  — Correcciones de errores exclusivamente
RC5.5.2  — Suite de tests institucionales
RC5.5.3  — Pruebas de estrés (100k registros, PC 2GB, USB lento)
RC5.5-LTS (90 días sin errores críticos) — Declaración LTS
RC6.0    — Solo después de LTS confirmado
```

---

## 7. Criterios para declarar RC5.5-LTS

Después de 90 días de operación:

- [ ] Errores críticos = 0 (pérdida de datos, corrupción, acceso no autorizado)
- [ ] Backups restaurables verificados mensualmente
- [ ] Sin incidentes de seguridad documentados
- [ ] Tests automatizados pasan 100%
- [ ] Logs sin excepciones no manejadas
- [ ] Todos los usuarios capacitados documentalmente

---

*Aprobado por: Comité Técnico SIGCA · RC5.5 · 2026-06-12*
