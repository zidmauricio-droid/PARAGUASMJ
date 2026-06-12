# MATRIZ DE COBERTURA DE PRUEBAS — PARAGUASMJ RC5.5
**Generado:** 2026-06-12 · **Versión:** RC5.5.2 · **Herramienta:** pytest-cov

---

## Resumen ejecutivo

| Métrica                | Valor       |
|------------------------|-------------|
| Cobertura total        | **21.5%**   |
| Sentencias totales     | 6 662       |
| Sentencias cubiertas   | ~1 432      |
| Tests ejecutados       | 79          |
| Tests fallidos         | 0           |
| Tiempo de ejecución    | < 30 s      |

> **Nota RC5.5:** El 21.5% de cobertura refleja la naturaleza de una aplicación Flask con múltiples rutas
> de interfaz de usuario que requieren integración completa para ser cubiertas. Los módulos de núcleo
> críticos (crypto, seguridad, backup) tienen cobertura superior al 35%.

---

## Cobertura por módulo

### Nivel 1 — Núcleo Institucional

| Módulo                          | Sentencias | Cobertura | Estado         | Prioridad RC6.0 |
|---------------------------------|:----------:|:---------:|----------------|:---------------:|
| `core/crypto_simple.py`         | 43         | **90.7%** | EXCELENTE      | —               |
| `core/seguridad.py`             | 22         | **68.2%** | BUENA          | —               |
| `core/csrf_manager.py`          | 26         | **38.5%** | MEDIA          | ALTA            |
| `core/database_manager.py`      | 83         | **45.8%** | BUENA          | MEDIA           |
| `core/backup_manager.py`        | 96         | **35.4%** | MEDIA          | ALTA            |
| `core/otp_manager.py`           | 107        | **17.8%** | BAJA           | ALTA            |
| `core/secure_auth.py`           | 34         | **0.0%**  | SIN COBERTURA  | MEDIA           |
| `core/auditoria.py`             | 8          | **50.0%** | BUENA          | —               |

### Nivel 1 — Rutas núcleo

| Módulo                          | Sentencias | Cobertura | Estado         | Prioridad RC6.0 |
|---------------------------------|:----------:|:---------:|----------------|:---------------:|
| `routes/autenticacion.py`       | 208        | **38.0%** | MEDIA          | ALTA            |
| `routes/auditoria.py`           | 200        | **27.0%** | BAJA           | ALTA            |
| `routes/documentos.py`          | 861        | **16.8%** | BAJA           | CRÍTICA         |
| `routes/expedientes.py`         | 100        | **29.0%** | BAJA           | ALTA            |

### Nivel 2 — Operación

| Módulo                          | Sentencias | Cobertura | Estado         | Prioridad RC6.0 |
|---------------------------------|:----------:|:---------:|----------------|:---------------:|
| `routes/pqrs.py`                | 357        | **17.4%** | BAJA           | ALTA            |
| `routes/finanzas.py`            | 287        | **29.3%** | BAJA           | ALTA            |
| `routes/balance_hidrico.py`     | 129        | **27.9%** | BAJA           | MEDIA           |
| `routes/convenios.py`           | 120        | **27.5%** | BAJA           | MEDIA           |
| `routes/emergencias.py`         | 507        | **17.6%** | BAJA           | MEDIA           |
| `routes/dashboard.py`           | 32         | **28.1%** | BAJA           | MEDIA           |
| `routes/gis.py`                 | 212        | **21.2%** | BAJA           | BAJA            |
| `routes/proyectos_v2.py`        | 426        | **23.2%** | BAJA           | MEDIA           |
| `routes/api.py`                 | 131        | **26.7%** | BAJA           | BAJA            |
| `routes/reportes_normativos.py` | 97         | **40.2%** | MEDIA          | MEDIA           |
| `routes/carpetas_bp.py`         | 81         | **39.5%** | MEDIA          | MEDIA           |
| `routes/comunicaciones.py`      | 41         | **26.8%** | BAJA           | BAJA            |

### Utilities

| Módulo                          | Sentencias | Cobertura | Estado         |
|---------------------------------|:----------:|:---------:|----------------|
| `utils/audit.py`                | 51         | **64.7%** | BUENA          |
| `utils/helpers.py`              | 23         | **65.2%** | BUENA          |
| `utils/seguridad.py`            | 89         | **36.0%** | MEDIA          |
| `utils/auditoria.py`            | 82         | **26.8%** | BAJA           |
| `utils/validadores.py`          | 55         | **23.6%** | BAJA           |
| `utils/file_manager.py`         | 124        | **16.9%** | BAJA           |
| `utils/validators.py`           | 27         | **0.0%**  | SIN COBERTURA  |
| `utils/compresor_imagen.py`     | 51         | **0.0%**  | SIN COBERTURA  |
| `utils/export_pdf.py`           | 86         | **0.0%**  | SIN COBERTURA  |

### Core — Sin cobertura (requieren tests RC6.0)

| Módulo                          | Sentencias | Motivo                              |
|---------------------------------|:----------:|-------------------------------------|
| `core/scheduler_notificaciones.py` | 90      | Requiere mock WhatsApp/Email        |
| `core/usb_updater.py`           | 150        | Requiere mock dispositivo USB       |
| `core/reportes_excel.py`        | 82         | Requiere mock openpyxl/pandas       |
| `core/pdf_profesional.py`       | 195        | Requiere mock WeasyPrint/reportlab  |
| `core/logo_manager.py`          | 139        | Requiere mock filesystem de statics |
| `core/multi_hash.py`            | 41         | Pendiente test hash múltiple        |
| `core/calendario_colombiano.py` | 68         | Pendiente test fechas festivas CO   |
| `core/baseline_config.py`       | 47         | Pendiente test config baseline      |
| `core/email_manager.py`         | 79         | Requiere mock SMTP                  |
| `core/weasyprint_fallback.py`   | 60         | Requiere mock PDF engine            |
| `core/verificador_wasm.py`      | 14         | Requiere mock WASM runtime          |

---

## Tests existentes (79 tests, 0 fallidos)

| Archivo                   | Tests | Módulos cubiertos                              |
|---------------------------|:-----:|------------------------------------------------|
| `tests/test_backup.py`    | 7     | backup_manager, crypto_simple, csrf_manager    |

---

## Hoja de ruta de cobertura

| Meta     | Versión | Cobertura objetivo | Tests requeridos                        |
|----------|---------|--------------------|-----------------------------------------|
| Actual   | RC5.5   | 21.5%              | 79 tests (7 archivos)                   |
| Fase 1   | RC5.5.3 | 35%                | +50 tests: autenticacion, documentos    |
| Fase 2   | RC5.6   | 50%                | +80 tests: pqrs, finanzas, expedientes  |
| Objetivo | RC6.0   | ≥ 60%              | +100 tests: scheduler mock, OTP mock    |

---

## Módulos críticos sin tests (prioridad máxima)

1. **`routes/documentos.py`** (861 sentencias, 16.8%) — módulo más grande del sistema
2. **`routes/pqrs.py`** (357 sentencias, 17.4%) — módulo regulatorio crítico
3. **`core/otp_manager.py`** (107 sentencias, 17.8%) — firmas digitales institucionales
4. **`core/scheduler_notificaciones.py`** (90 sentencias, 0%) — notificaciones PQRS

---

*Generado desde `docs/coverage.json` · Cobertura medida con `pytest --cov=. --cov-report=json`*
