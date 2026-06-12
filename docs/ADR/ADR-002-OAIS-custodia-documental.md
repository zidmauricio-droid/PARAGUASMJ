# ADR-002: OAIS como Modelo de Custodia Documental
**Estado:** ACEPTADO · **Fecha:** 2026-06-12 · **Versión:** RC5.5

## Contexto
Los documentos gestionados por SIGCA tienen valor legal (contratos, actas, PQRS, reportes SUI). La pérdida o alteración de estos documentos puede generar sanciones de la SSPD o la CRA.

## Decisión
El modelo de custodia documental sigue el estándar **OAIS (Open Archival Information System, ISO 14721:2012)**.

## Implementación en RC5.5
- **Ingesta:** Validación de tipo documental + timestamp en `registro_central`
- **Almacenamiento archivístico:** `expedientes` + PDF generado por `core/pdf_profesional.py`
- **Gestión de datos:** `seguimiento_documento` + `audit_log`
- **Acceso:** Control de roles en todos los endpoints
- **Administración:** `configuracion_historial` + `logs_sistema`

## Consecuencias
- Todo documento debe tener `codigo_completo` único e irrepetible
- El estado `Archivado` activa protección WORM
- Las migraciones de formato deben registrarse en `audit_log`

## Revisión
Revisión ante cambio normativo del AGN (Archivo General de la Nación) o ante cambio de marco legal de preservación digital.
