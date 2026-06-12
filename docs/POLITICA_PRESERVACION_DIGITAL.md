# POLÍTICA DE PRESERVACIÓN DIGITAL — PARAGUASMJ SIGCA
**Versión:** 1.0 · **Fecha:** 2026-06-12  
**Marco normativo:** Ley 594/2000 (Ley General de Archivos), OAIS ISO 14721:2012, Acuerdo AGN 003/2013

---

## 1. Alcance

Esta política regula la preservación de documentos digitales gestionados por PARAGUASMJ SIGCA para ASUACAP (Acueducto Comunitario El Puente, Villeta, Cundinamarca) y cualquier organización usuaria del sistema.

---

## 2. Principios OAIS Implementados

| Principio OAIS | Implementación en SIGCA |
|---------------|------------------------|
| Submission (Ingesta) | `registro_central` + validación de tipo documental |
| Archival Storage | `expedientes` + columna `ruta_archivo_pdf` |
| Data Management | `registro_central` + `documento_firmantes` + `seguimiento_documento` |
| Preservation Planning | Baseline RC5.5 congelada, versionado formal |
| Access | Control de roles (`login_requerido`, `rol_requerido`) |
| Administration | `audit_log`, `logs_sistema`, `configuracion_historial` |

---

## 3. Tabla de Retención Documental

| Tipo de Documento | Retención Mínima | Base Legal |
|------------------|-----------------|-----------|
| PQRS (Peticiones, Quejas, Reclamos) | 5 años | Ley 1755/2015, circular SSPD |
| Documentos financieros (facturas, contratos) | 10 años | Estatuto Tributario Art. 632 |
| Actas de junta directiva | Permanente | Ley 594/2000 |
| Reportes SUI | 10 años | Ley 142/1994 + res. SSPD |
| PUEAA (Plan de Uso Eficiente del Agua) | Vigencia + 5 años | CRA 906/2019 |
| Contratos de servicio | Vigencia + 10 años | Código Civil |
| Expedientes de suscriptores | Activo + 5 años post-retiro | Reglamento interno |
| Registros de auditoría (`audit_log`) | 7 años | Ley 594/2000 Art. 46 |

---

## 4. Integridad Documental

Cada documento en `registro_central` debe tener:

- `codigo_completo` — identificador único e irrepetible
- `fecha_creacion` — timestamp de ingesta
- `creado_por` — usuario responsable
- Estado en `audit_log` al momento de creación

**WORM (Write Once Read Many):** Los documentos en estado `Archivado` no pueden modificarse. Solo el administrador puede cambiar este estado con registro en `audit_log`.

---

## 5. Migración de Formato

Cuando un formato quede obsoleto (ej: .doc → .docx → .odt):

1. Crear entrada de migración en `audit_log` con evento `FORMATO_MIGRADO`
2. Conservar el archivo original hasta verificar la copia migrada
3. Actualizar `ruta_archivo_pdf` en `registro_central`
4. Documentar la migración en `expedientes.observaciones`

---

## 6. Verificación Periódica de Integridad

| Frecuencia | Acción | Responsable |
|-----------|--------|-------------|
| Diaria | Backup automático con `integrity_check` | Sistema |
| Mensual | `backup_test_restore()` manual | Administrador |
| Anual | Auditoría completa de expedientes vencidos | Comité técnico |
| Ante actualización | Backup manual + verificación antes de aplicar | Administrador |

---

## 7. Disposición Final

Un documento puede:

- **Conservarse permanentemente** — migrar a soporte físico certificado o sistema de archivo histórico
- **Eliminarse** — solo con acto administrativo documentado y registro en `audit_log`
- **Transferirse** — a otra entidad con acta de transferencia y registro en expediente

La eliminación de documentos desde SIGCA **no elimina la obligación de conservar** los originales en soporte físico cuando la ley así lo exija.

---

*Revisión anual obligatoria. Vigencia: RC5.5 en adelante.*
