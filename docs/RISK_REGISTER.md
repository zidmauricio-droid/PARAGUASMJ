# MATRIZ DE RIESGOS — PARAGUASMJ RC5.5
**Baseline:** PARAGUASMJ-RC5.5-20260612 · **Fecha:** 2026-06-12
**Responsable:** SIGCA — Equipo técnico PARAGUASMJ

---

## Escala de valoración

| Probabilidad | Valor | Impacto     | Valor |
|--------------|-------|-------------|-------|
| Muy alta     | 5     | Catastrófico| 5     |
| Alta         | 4     | Alto        | 4     |
| Media        | 3     | Medio       | 3     |
| Baja         | 2     | Bajo        | 2     |
| Muy baja     | 1     | Mínimo      | 1     |

**Riesgo residual = Probabilidad × Impacto** (umbral crítico ≥ 12)

---

## Riesgos Técnicos

| ID   | Descripción                          | P | I | Residual | Estado        | Mitigación RC5.5                              | Plan RC6.0                        |
|------|--------------------------------------|---|---|----------|---------------|-----------------------------------------------|-----------------------------------|
| RT-1 | Falla HDD / pérdida total de datos   | 2 | 5 | **10**   | CONTROLADO    | Backup automático diario + integrity_check    | Backup externo cifrado (Fernet)   |
| RT-2 | Corrupción SQLite (WAL desincronizado)| 2 | 5 | **10**  | CONTROLADO    | WAL mode + PRAGMA integrity_check en backup   | pg_dump opcional para migración   |
| RT-3 | Cifrado débil de secretos (XOR-SHA)  | 3 | 3 | **9**    | DOCUMENTADO   | es_cifrado_institucional()==False + audit     | cryptography.Fernet               |
| RT-4 | USB updater sin verificación de autoría| 2 | 4 | **8**  | PARCIAL       | manifest.sha256 + zipfile.testzip()           | manifest.sig Ed25519              |
| RT-5 | Sesiones concurrentes no controladas | 3 | 2 | **6**    | ACEPTADO      | Política institucional (decisión organizacional)| tabla sesiones_activas           |
| RT-6 | Saldo financiero lento >50k registros| 2 | 3 | **6**    | MITIGADO      | Índices en movimientos_financieros + caja_chica| ledger_balance por trigger       |
| RT-7 | CSRF triple coexistencia residual    | 1 | 3 | **3**    | MITIGADO      | csrf_manager.py como autoridad única          | Eliminar utils/seguridad fuente  |

---

## Riesgos Operativos

| ID   | Descripción                              | P | I | Residual | Estado     | Mitigación RC5.5                             | Plan RC6.0                     |
|------|------------------------------------------|---|---|----------|------------|----------------------------------------------|--------------------------------|
| RO-1 | Error humano — eliminación accidental    | 3 | 4 | **12**   | CONTROLADO | WORM en estado=Archivado + audit_log completo| Papelera institucional         |
| RO-2 | Pérdida de continuidad (un solo técnico) | 2 | 4 | **8**    | DOCUMENTADO| ADRs + BASELINE_OPERATIVA + guías técnicas   | Manual operador certificado    |
| RO-3 | Notificación silenciosa (WhatsApp falla) | 3 | 3 | **9**    | MITIGADO   | Fallback WhatsApp→Email→Log + audit canal    | Canal redundante (SMS)         |
| RO-4 | OTP sin entrega (sin WhatsApp/email)     | 2 | 3 | **6**    | MITIGADO   | OTP_GENERADO_SIN_ENVIO auditado              | OTP por SMS alternativo        |
| RO-5 | PQRS vencida sin alerta                  | 2 | 4 | **8**    | CONTROLADO | Dashboard /api/salud + pqrs_vencidas KPI     | Alerta automática multi-canal  |

---

## Riesgos de Seguridad

| ID   | Descripción                              | P | I | Residual | Estado     | Mitigación RC5.5                                | Plan RC6.0                    |
|------|------------------------------------------|---|---|----------|------------|-------------------------------------------------|-------------------------------|
| RS-1 | Inyección SQL en filtros de búsqueda     | 1 | 5 | **5**    | CONTROLADO | Parámetros preparados en todas las consultas    | —                             |
| RS-2 | Path traversal en backup/foto            | 1 | 4 | **4**    | CONTROLADO | safe_join() + regex estricta en servir_foto     | —                             |
| RS-3 | Fuerza bruta en login                    | 2 | 4 | **8**    | CONTROLADO | bloqueado=1 tras 5 intentos + audit LOGIN_FAILED| 2FA obligatorio               |
| RS-4 | CSRF en operaciones mutantes             | 1 | 4 | **4**    | CONTROLADO | csrf_requerido() decorator en todas las rutas POST| —                           |
| RS-5 | XSS en campos de texto libre             | 2 | 3 | **6**    | PARCIAL    | Jinja2 autoescaping habilitado                  | CSP headers RC6.0             |
| RS-6 | Exposición de credenciales en BD        | 2 | 4 | **8**    | MITIGADO   | Ofuscación XOR-SHA (crypto_simple) + audit      | Fernet + vault de secretos    |

---

## Mapa de calor

```
Impacto
5 │ RT-1 RT-2 │         │ RO-1    │
4 │           │ RS-3 RS-6│ RO-2    │ RT-4
3 │ RT-3 RT-7 │ RO-3 RS-5│        │
2 │           │ RT-5 RT-6│         │
1 │           │ RS-1 RS-4│ RS-2    │
  └───────────┼──────────┼─────────┼────
              1          2         3    P
```

---

## Riesgos críticos (residual ≥ 12)

| ID   | Riesgo                      | Acción inmediata                    |
|------|-----------------------------|-------------------------------------|
| RO-1 | Error humano — eliminación  | Confirmar WORM activo en DB         |

---

## Historial de cambios

| Versión | Fecha      | Cambio                          |
|---------|------------|---------------------------------|
| v1.0    | 2026-06-12 | Creación inicial — RC5.5.2      |
