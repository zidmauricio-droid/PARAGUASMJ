# ADR-003: WORM para Documentos Archivados
**Estado:** ACEPTADO · **Fecha:** 2026-06-12 · **Versión:** RC5.5

## Contexto
Los documentos en estado `Archivado` no deben poder modificarse. Esto es un requisito legal (Ley 594/2000) y un requisito de integridad (evitar manipulación de registros históricos).

## Decisión
Los documentos en estado `Archivado` en `registro_central` tienen protección **WORM (Write Once Read Many)** implementada a nivel de aplicación:
- Los endpoints de edición verifican el estado antes de permitir cambios
- Cambiar un documento de `Archivado` a otro estado requiere rol `admin` y queda registrado en `audit_log`

## Limitaciones
Esta es una protección a nivel de aplicación, no a nivel de sistema de archivos. Un administrador de BD con acceso directo a SQLite puede modificar registros. Para protección absoluta se requiere firma digital criptográfica (planificado RC6.0).

## Plan RC6.0
Agregar `hash_contenido` (SHA-256 del contenido del documento) al momento del archivado, verificable independientemente del sistema.

## Revisión
Ante cambio normativo o implementación de firma digital.
