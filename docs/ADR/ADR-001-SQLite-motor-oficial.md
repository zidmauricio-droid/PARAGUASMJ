# ADR-001: SQLite como Motor de Base de Datos Oficial
**Estado:** ACEPTADO · **Fecha:** 2026-06-12 · **Versión:** RC5.5

## Contexto
PARAGUASMJ opera en acueductos comunitarios rurales de Colombia, frecuentemente sin acceso a internet, con equipos modestos (2-4 GB RAM, discos HDD), y sin personal TI permanente.

## Decisión
SQLite en modo **WAL (Write-Ahead Logging)** es el motor de base de datos oficial y único.

## Consecuencias Positivas
- Sin servidor de BD que administrar — operación completamente local
- Backup es una copia de un único archivo `.db`
- Compatible con PyInstaller para distribución `.exe`
- Rendimiento adecuado para < 500 usuarios concurrentes
- `PRAGMA foreign_keys=ON` garantiza integridad referencial
- `PRAGMA journal_mode=WAL` permite lecturas concurrentes sin bloqueo

## Consecuencias Negativas / Limitaciones
- No escala a más de ~500 escrituras concurrentes simultáneas
- No soporta stored procedures ni triggers complejos nativamente
- Replicación multi-nodo requiere solución externa

## Alternativas Rechazadas
- **PostgreSQL**: requiere servidor, administración, conocimiento TI — incompatible con contexto rural
- **MySQL/MariaDB**: misma razón
- **MongoDB**: sin soporte para transacciones ACID en todas las versiones

## Revisión
Esta decisión no debe revisarse antes de RC7.0 o ante un crecimiento documentado de > 1000 usuarios concurrentes.
