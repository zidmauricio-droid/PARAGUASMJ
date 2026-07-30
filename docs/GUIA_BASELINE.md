# PARAGUASMJ — Guía de Baseline RC5.5

## ¿Qué es la Baseline?

La **Baseline RC5.5** es el núcleo institucional del sistema PARAGUASMJ. Representa el
conjunto mínimo de componentes que garantizan:

- Valor probatorio de los documentos (Ley 594/2000)
- Cadena de custodia ininterrumpida
- Integridad y autenticidad verificables
- Cumplimiento OAIS (Modelo de Referencia ISO 14721)
- Trazabilidad de 10 años

## Arquitectura de tres capas

```
┌─────────────────────────────────────────────────────────────┐
│              CAPA 1 — NÚCLEO CONGELADO (RC5.5)              │
│  Identity Hash · Chain Fingerprint · Epoch Registry         │
│  Merkle Registry · Verification Registry · OAIS · WORM      │
│  Capability Registry · Baseline Lock                        │
│  ► INMODIFICABLE sin autorización del desarrollador         │
├─────────────────────────────────────────────────────────────┤
│              CAPA 2 — MÓDULOS OPERATIVOS                    │
│  Documentos · PQRS · GIS · Proyectos · Finanzas            │
│  Contactos · TRD · Calendario · OTP · Firmantes             │
│  ► Mantenibles en producción                                │
├─────────────────────────────────────────────────────────────┤
│              CAPA 3 — EXTENSIONES RC6.0 (DESHABILITADAS)    │
│  Expedientes · Multi TSA · Blockchain · Notary              │
│  Hardware Trust · OCSP/CRL · Crypto Renewal · AIP           │
│  ► Experimentales — requieren activación explícita          │
└─────────────────────────────────────────────────────────────┘
```

## Componentes congelados RC5.5

| Componente | Propósito |
|---|---|
| `identity_hash` | Huella digital única de cada documento |
| `chain_fingerprint` | Enlace criptográfico entre documentos sucesivos |
| `epoch_registry` | Registro temporal sellado |
| `merkle_registry` | Árbol de Merkle para verificación masiva |
| `verification_registry` | Registro de verificaciones realizadas |
| `oais` | Conformidad con ISO 14721 (preservación largo plazo) |
| `worm` | Write-Once-Read-Many — inmutabilidad del archivo |
| `capability_registry` | Registro de capacidades habilitadas |
| `baseline_lock` | Candado que impide modificaciones no autorizadas |
| `architectural_constraints` | Reglas que mantienen coherencia del sistema |

## Extensiones RC6.0 — ¿por qué están deshabilitadas?

Las extensiones RC6.0 son **opcionales**. Su ausencia **NO invalida** el valor
probatorio de ningún documento ya almacenado. Esto es una garantía legal explícita.

Para activar una extensión:

```python
from core.baseline_config import BaselineController
ctrl = BaselineController()
result = ctrl.enable_optional_module("expedientes")
# Si result["requires_migration"] == True:
#   ejecutar migrations/013_expedientes.sql ANTES de activar
```

## Garantías legales a 10 años

La ausencia de módulos RC6.0 **no invalida**:

1. **Valor probatorio** — los documentos siguen siendo válidos ante autoridades
2. **Cadena de custodia** — el hash chain RC5.5 garantiza integridad
3. **Integridad** — SHA-256 + SHA3-256 + BLAKE2b verificables en cualquier momento
4. **Autenticidad** — firma OTP de firmantes registrada en la cadena
5. **Trazabilidad** — log HMAC-SHA256 inalterable
6. **Cumplimiento OAIS** — conforme ISO 14721 con los componentes RC5.5

## Verificar integridad en cualquier momento

```bash
# Desde la carpeta del proyecto
python -c "
from core.baseline_config import BaselineController
report = BaselineController().get_baseline_report()
print('Integridad OK:', report['integrity_ok'])
print('Baseline ID:', report['baseline_id'])
"
```
