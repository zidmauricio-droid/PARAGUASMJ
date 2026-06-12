# ACTA DE CONGELAMIENTO — BASELINE INSTITUCIONAL RC5.5
**Número:** SIGCA-ACTA-2026-001
**Fecha:** 2026-06-12
**Versión:** RC5.5 (Release Candidate 5.5)
**Baseline ID:** PARAGUASMJ-RC5.5-20260612

---

## 1. Identificación del Sistema

| Campo              | Valor                                                    |
|--------------------|----------------------------------------------------------|
| Sistema            | PARAGUASMJ — Sistema de Gestión Documental SIGCA         |
| Entidad            | ASUACAP — Acueducto Comunitario El Puente                |
| Municipio          | Villeta, Cundinamarca, Colombia                          |
| Responsable técnico| SIGCA — Equipo técnico PARAGUASMJ                        |
| Versión congelada  | RC5.5                                                    |
| Fecha congelamiento| 2026-06-12                                               |

---

## 2. Hash de Integridad

```
Baseline Hash (SHA-256 de todos los archivos .py):
40c32ceb7a860fce8bfa95796b253cbf5609dfdca32459c7f7d2c09728db251a

Comando de verificación:
find PARAGUASMJ/ -name "*.py" | sort | xargs sha256sum | sha256sum
```

Este hash permite verificar en cualquier momento que el núcleo del sistema
no ha sido modificado sin autorización.

---

## 3. Componentes del Baseline

### Nivel 1 — Núcleo Institucional (CONGELADO)

| Módulo                        | Archivo                          | Estado    |
|-------------------------------|----------------------------------|-----------|
| Autenticación + OTP           | routes/autenticacion.py          | CONGELADO |
| Gestión documental            | routes/documentos.py             | CONGELADO |
| Expedientes digitales         | routes/expedientes.py            | CONGELADO |
| Auditoría + usuarios          | routes/auditoria.py              | CONGELADO |
| Backup WAL-safe               | core/backup_manager.py           | CONGELADO |
| CSRF — autoridad única        | core/csrf_manager.py             | CONGELADO |
| OTP firmas digitales          | core/otp_manager.py              | CONGELADO |
| Gestor de BD                  | core/database_manager.py         | CONGELADO |

### Nivel 2 — Operación (CONTROLADO — solo parches)

| Módulo                        | Archivo                          | Estado      |
|-------------------------------|----------------------------------|-------------|
| PQRS                          | routes/pqrs.py                   | CONTROLADO  |
| Finanzas                      | routes/finanzas.py               | CONTROLADO  |
| Balance hídrico               | routes/balance_hidrico.py        | CONTROLADO  |
| Convenios                     | routes/convenios.py              | CONTROLADO  |
| Emergencias GIS               | routes/emergencias.py            | CONTROLADO  |
| Dashboard + salud             | routes/dashboard.py              | CONTROLADO  |
| Scheduler notificaciones      | core/scheduler_notificaciones.py | CONTROLADO  |

### Nivel 3 — Extensiones (RC6.0+, NO ACTIVADAS)

| Módulo                        | Archivo                                        | Estado    |
|-------------------------------|------------------------------------------------|-----------|
| Clasificador archivístico IA  | modules/documental/clasificador_documental.py  | DESACTIVADO |
| Cifrado institucional Fernet  | (pendiente RC6.0)                              | PENDIENTE |
| Multi-tenant                  | (pendiente RC6.0)                              | PENDIENTE |
| Backup externo cifrado        | (pendiente RC6.0)                              | PENDIENTE |

---

## 4. Métricas de Calidad al Cierre

| Indicador                    | Valor RC5.5  |
|------------------------------|--------------|
| Tests unitarios pasando      | 79 / 79      |
| Tests fallidos               | 0            |
| Cobertura total              | 21%          |
| Correcciones de seguridad    | 39           |
| Commits de estabilización    | 8+           |
| ADRs documentados            | 4            |
| Políticas documentadas       | 3            |
| Riesgos registrados          | 18           |
| Riesgos críticos pendientes  | 1 (RO-1)     |

---

## 5. Calificación Institucional

| Dimensión                | Calificación |
|--------------------------|:------------:|
| Seguridad                | 9.2 / 10     |
| Robustez operativa       | 9.0 / 10     |
| Operación rural offline  | 9.5 / 10     |
| Auditoría institucional  | 9.0 / 10     |
| Finanzas                 | 8.5 / 10     |
| Compatibilidad RC5.5     | 9.8 / 10     |
| Baseline institucional   | 9.2 / 10     |

---

## 6. Condiciones del Congelamiento

1. El Nivel 1 (Núcleo Institucional) **no recibe nuevas funcionalidades** a partir de esta fecha.
2. Solo se aceptan **parches de corrección** (`RC5.5.x`) para errores documentados y verificados.
3. Las nuevas funcionalidades van a ramas de desarrollo **RC6.0**, no al núcleo.
4. Toda modificación de un componente congelado requiere:
   - Actualizar `docs/ARCHITECTURE_MANIFEST.yaml`
   - Recalcular el `baseline_hash`
   - Crear un nuevo ADR si aplica
   - Aprobación del comité técnico

---

## 7. Criterios de Liberación de RC6.0

RC6.0 solo inicia formalmente cuando RC5.5 cumpla:
- **90 días de operación** sin errores críticos en producción
- Cobertura de tests ≥ 40%
- Cifrado institucional migrado a `cryptography.Fernet`
- Backup externo configurado y verificado

---

## 8. Firmas (Acta institucional)

| Rol                    | Nombre           | Firma     | Fecha      |
|------------------------|------------------|-----------|------------|
| Responsable técnico    | Equipo SIGCA     | _______   | 2026-06-12 |
| Representante ASUACAP  | _______________  | _______   | 2026-06-12 |
| Revisor externo        | _______________  | _______   | 2026-06-12 |

---

*Este documento es parte del expediente de gobernanza técnica de PARAGUASMJ.*
*Conservar junto con `docs/ARCHITECTURE_MANIFEST.yaml` y `docs/baseline_hash.txt`.*
