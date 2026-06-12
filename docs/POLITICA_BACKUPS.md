# POLÍTICA DE BACKUPS — PARAGUASMJ SIGCA
**Versión:** 1.0 · **Fecha:** 2026-06-12  
**Módulo responsable:** `core/backup_manager.py`

---

## 1. Frecuencia

| Tipo | Frecuencia | Responsable |
|------|-----------|-------------|
| Backup automático diario | Todos los días a las 08:00 | APScheduler (`core/scheduler_notificaciones.py`) |
| Backup manual | Antes de cualquier actualización USB | Administrador del sistema |
| Backup antes de restauración | Automático, previo a `restaurar_backup()` | Sistema |

---

## 2. Retención

- Se mantienen los **10 backups más recientes** (`Config.BACKUPS_A_MANTENER = 10`)
- Se eliminan automáticamente los backups con **más de 30 días** de antigüedad
- Los dos criterios se aplican simultáneamente; el más estricto prevalece

---

## 3. Ubicación

```
database/backups/paraguasmj_YYYYMMDD_HHMMSS.db
```

Los backups **nunca** deben almacenarse en el mismo disco que la base de datos activa cuando sea posible.

---

## 4. Verificación de Integridad

Todo backup creado pasa automáticamente por:

1. **`PRAGMA integrity_check`** — verifica estructura interna SQLite
2. **`backup_test_restore()`** — consulta funcional de tablas críticas:
   - `usuarios`
   - `registro_central`
   - `audit_log`
   - `configuracion`

Si alguna verificación falla, el backup se elimina y se registra en el log.

---

## 5. Restauración

**Procedimiento:**

```bash
# Desde la interfaz web: /backup/crear (POST, requiere admin)
# Desde código: core/backup_manager.restaurar_backup(ruta)
```

**Validaciones previas a restauración:**
- Verificación de ruta (path traversal guard)
- `PRAGMA integrity_check` sobre el archivo de origen
- Consulta funcional de tablas críticas

---

## 6. Responsable

- **Creación automática:** APScheduler (sin intervención humana)
- **Verificación mensual:** Administrador del sistema — ejecutar `backup_test_restore()` manualmente
- **Restauración:** Solo el administrador, con documentación del incidente en `audit_log`

---

## 7. Eventos de Auditoría

Todos los eventos de backup se registran en `audit_log`:

| Evento | Descripción |
|--------|-------------|
| `BACKUP_CREADO` | Backup exitoso con ruta y tablas verificadas |
| `BACKUP_FALLIDO` | Error durante creación |
| `BACKUP_CORRUPTO` | integrity_check o test_restore falló — backup eliminado |
| `BACKUP_RESTAURADO` | Restauración exitosa |

---

*Vigencia: RC5.5 — Revisión anual o ante cambio de motor de base de datos*
