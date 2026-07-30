# Playbook de Recuperación ante Desastres — PARAGUASMJ RC5.5
**Entidad:** ASUACAP — Acueducto Comunitario El Puente · Villeta, Cundinamarca
**Versión:** RC5.5 · **Fecha:** 2026-06-12

---

## 1. Archivos críticos a respaldar

| Archivo / Carpeta             | Descripción                         | Frecuencia backup |
|-------------------------------|-------------------------------------|:-----------------:|
| `database/paraguasmj.db`      | Base de datos principal (104 tablas)| Diario automático |
| `database/backups/*.db`       | Backups automáticos del sistema     | Conservar 10      |
| `uploads/`                    | Documentos adjuntos                 | Semanal manual    |
| `config.py`                   | Configuración institucional         | Al modificar      |
| `.app_secret`                 | Clave de sesión persistida          | Al crear          |
| `logs/paraguasmj.log*`        | Logs rotativos (5 archivos x 5MB)   | Opcional          |

**Ubicación del backup automático:** `database/backups/paraguasmj_YYYYMMDDHHMMSS.db`

---

## 2. Escenario A — Falla de disco / pérdida total

### Prerrequisitos
- Python 3.11+
- Backup de `database/backups/*.db` disponible

### Pasos de recuperación

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Verificar integridad del backup antes de restaurar
sqlite3 /ruta/backup.db "PRAGMA integrity_check"
# Debe retornar: ok

# 3. Copiar backup como BD principal
cp /ruta/backup.db database/paraguasmj.db

# 4. Inicializar tablas faltantes (idempotente — no borra datos)
python database/inicializar_db.py

# 5. Verificar WORM y cadena de custodia
python -c "
from core.database_manager import get_db
conn = get_db()
total = conn.execute('SELECT COUNT(*) FROM registro_central').fetchone()[0]
print(f'Documentos recuperados: {total}')
conn.close()
"

# 6. Iniciar servidor
python app.py
```

---

## 3. Escenario B — Corrupción de SQLite

```bash
# 1. Diagnosticar
sqlite3 database/paraguasmj.db "PRAGMA integrity_check"

# 2. Si falla, recuperar con la herramienta de SQLite
sqlite3 database/paraguasmj.db ".dump" | sqlite3 database/paraguasmj_recovered.db

# 3. Verificar recuperado
sqlite3 database/paraguasmj_recovered.db "PRAGMA integrity_check"

# 4. Reemplazar si ok
cp database/paraguasmj.db database/paraguasmj_corrupted_$(date +%Y%m%d).db
cp database/paraguasmj_recovered.db database/paraguasmj.db
```

---

## 4. Escenario C — Reinicio de servidor (pérdida de sesiones)

Con la configuración RC5.5 (`SESSION_TYPE=filesystem`), las sesiones sobreviven al reinicio automáticamente. Solo se pierden si se borra `instance/flask_sessions/`.

```bash
# Si se perdieron sesiones, los usuarios simplemente vuelven a iniciar sesión.
# No hay pérdida de datos.
```

---

## 5. Verificación de integridad post-recuperación

```bash
# Endpoint de salud institucional
curl http://localhost:5000/api/salud

# Debe retornar:
# {"ok": true, "integrity_check": "ok", "pqrs_vencidas": N, ...}
```

También disponible en el panel: **Dashboard → Salud Institucional**

---

## 6. Verificación del baseline

```bash
# Verificar que el código no fue alterado
find . -name "*.py" | sort | xargs sha256sum | sha256sum

# Comparar con:
# 40c32ceb7a860fce8bfa95796b253cbf5609dfdca32459c7f7d2c09728db251a
```

---

## 7. Contactos de soporte técnico

| Rol                   | Responsabilidad                     |
|-----------------------|-------------------------------------|
| Técnico SIGCA         | Instalación, BD, backup, red        |
| Presidente ASUACAP    | Autorizar restauración de datos     |
| Revisor externo       | Auditoría post-recuperación         |

---

## 8. Checklist de recuperación

- [ ] BD restaurada desde backup verificado
- [ ] `PRAGMA integrity_check` retorna `ok`
- [ ] Endpoint `/api/salud` retorna `"ok": true`
- [ ] Usuario `admin` puede iniciar sesión
- [ ] Documentos visibles en módulo Documentos
- [ ] Al menos 1 PQRS visible en módulo PQRS
- [ ] Backup automático configurado y funcionando

---

*Conservar este documento en papel y en backup externo.*
*Última actualización: 2026-06-12 · PARAGUASMJ RC5.5*
