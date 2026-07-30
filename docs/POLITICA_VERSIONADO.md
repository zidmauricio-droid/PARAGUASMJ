# POLÍTICA DE VERSIONADO — PARAGUASMJ SIGCA
**Versión:** 1.0 · **Fecha:** 2026-06-12  
**Alcance:** Todo el ciclo de vida del software PARAGUASMJ SIGCA

---

## 1. Esquema de Versiones

```
RC[Mayor].[Menor].[Parche]
```

| Componente | Criterio de cambio |
|-----------|-------------------|
| **Mayor** (`RC5` → `RC6`) | Cambio arquitectónico irreversible, nueva baseline, ruptura de compatibilidad |
| **Menor** (`RC5.5` → `RC5.6`) | Nuevos módulos de Nivel 2, cambios de esquema retrocompatibles |
| **Parche** (`RC5.5.0` → `RC5.5.1`) | Correcciones de errores exclusivamente, sin nuevas funcionalidades |

---

## 2. Ramas de Git

| Rama | Propósito |
|------|-----------|
| `main` | Código en producción (solo versiones certificadas) |
| `claude/blissful-franklin-p9g7U` | Desarrollo activo RC5.5 |
| `fix/RC5.5.x-descripcion` | Parches de corrección |
| `feat/RC6.0-descripcion` | Nuevas funcionalidades (futuro) |

---

## 3. Procedimiento de Liberación

1. Congelar rama de desarrollo
2. Ejecutar suite de tests (`python -m pytest tests/ -v`)
3. Verificar sintaxis (`python3 -c "import ast; ast.parse(...)"`)
4. Actualizar `ARCHITECTURE_MANIFEST.yaml` → `baseline_id`
5. Generar ZIP con nombre normalizado: `PARAGUASMJ_SIGCA_RC[X.Y.Z]_YYYYMMDD.zip`
6. Calcular SHA-256 del ZIP y registrarlo en `docs/RELEASES.md`
7. Crear tag Git: `git tag -a RC5.5.0 -m "Baseline institucional"`

---

## 4. Compatibilidad Garantizada

RC5.5 garantiza compatibilidad hacia atrás con:
- Bases de datos creadas desde RC5.0 en adelante
- Actualizaciones USB desde RC5.3 en adelante
- Backups creados desde RC5.0 en adelante

---

## 5. Retiro de Versiones

Una versión se retira cuando:
- Han pasado 2 versiones menores (RC5.7 retira RC5.5)
- O existe una vulnerabilidad crítica no parcheable

---

*Vigencia: Desde RC5.5.0 hasta declaración de RC6.0*
