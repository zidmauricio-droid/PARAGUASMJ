# ADR-004: Congelamiento de Baseline RC5.5
**Estado:** ACEPTADO · **Fecha:** 2026-06-12 · **Versión:** RC5.5

## Contexto
El sistema ha acumulado 38 correcciones de seguridad y estabilidad. El riesgo principal ya no es la falta de funcionalidades, sino la posibilidad de **romper algo que ya funciona** al seguir agregando módulos.

## Decisión
A partir del 2026-06-12, RC5.5 se declara **Baseline Institucional Congelada**:

1. El Nivel 1 (Núcleo Institucional) no recibe nuevas funcionalidades
2. Solo se aceptan parches de corrección (`RC5.5.x`) para errores documentados
3. Las nuevas funcionalidades van a ramas de desarrollo RC6.0, no al núcleo
4. La arquitectura de tres niveles (Núcleo / Operación / Extensiones) es obligatoria

## Criterio de Liberación de RC6.0
RC6.0 solo inicia cuando RC5.5 cumpla **90 días de operación sin errores críticos** (ver `BASELINE_OPERATIVA_RC5.5.md`).

## Consecuencias
- Mejora la mantenibilidad a largo plazo
- Reduce la carga de pruebas en cada actualización
- Facilita soporte por terceros (técnicos externos pueden entender el núcleo estable)
- Limita temporalmente la velocidad de entrega de nuevas funcionalidades

## Alternativas Rechazadas
- **Desarrollo continuo sin congelamiento:** Aumenta complejidad, reduce estabilidad, dificulta auditorías

## Revisión
Esta decisión solo puede revisarse con votación formal del comité técnico.
