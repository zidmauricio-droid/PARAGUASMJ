# BASELINE DECLARATION — PARAGUASMJ RC5.5

**Fecha de congelación:** 2026-06-07  
**Perfil base:** `standard`  
**Responsable:** ASUACAP — Asociación de Suscriptores del Acueducto Comunitario El Puente  

---

## Propósito

Este baseline establece la identidad criptográfica del sistema en el momento de su activación formal. Los documentos generados a partir de esta fecha incluyen hashes multi-algoritmo que permiten verificar su autenticidad independientemente de cambios futuros en Python, Flask, SQLite o cualquier dependencia externa.

## Garantía de verificabilidad a largo plazo

| Horizonte | Mecanismo de verificación |
|-----------|--------------------------|
| 1-5 años  | Sistema activo + BD SQLite |
| 5-10 años | Verificador HTML standalone (SHA-256 via Web Crypto API) |
| 10-20 años | Comando Python: `hashlib.sha256(open(f,'rb').read()).hexdigest()` |
| 20+ años  | SHA-256 y SHA3-256 son estándares NIST — verificables con cualquier herramienta criptográfica |

## Algoritmos registrados

- **SHA-256**: estándar NIST FIPS 180-4
- **SHA3-256**: estándar NIST FIPS 202 (Keccak)
- **BLAKE2b-256**: RFC 7693 — resistente a ataques de extensión de longitud

La redundancia triple garantiza que el fallo futuro de un algoritmo no invalida la verificabilidad de los documentos.

## Verificación manual (sin sistema)

```bash
# SHA-256
python -c "import hashlib; print(hashlib.sha256(open('doc.pdf','rb').read()).hexdigest())"

# SHA3-256
python -c "import hashlib; print(hashlib.sha3_256(open('doc.pdf','rb').read()).hexdigest())"

# BLAKE2b-256
python -c "import hashlib; print(hashlib.blake2b(open('doc.pdf','rb').read(), digest_size=32).hexdigest())"
```

## Limitaciones conocidas

- SHA-3 y BLAKE2b no están disponibles en la Web Crypto API de navegadores — el verificador HTML sólo verifica SHA-256 de forma automática. Los otros dos requieren verificación manual por línea de comandos.
- La integridad del verificador HTML en sí debe comprobarse con el SHA-256 del archivo `.html` antes de usarlo como herramienta de auditoría.

## Inmutabilidad

Una vez registrado el hash de un documento, no debe modificarse. Cualquier versión nueva del documento genera un nuevo registro multi-hash. El registro histórico es append-only en la tabla `documento_multi_hash`.
