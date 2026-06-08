# PARAGUASMJ — Guía de Seguridad para Clientes Rurales

## ¿Quién puede hacer qué?

| Acción | Clientes / Usuarios | Desarrollador |
|---|:---:|:---:|
| Ver documentos | ✅ | ✅ |
| Crear documentos | ✅ | ✅ |
| Aprobar documentos (OTP) | ✅ | ✅ |
| Actualizar el sistema | ✅ (solo pull) | ✅ |
| Modificar el código | ❌ | ✅ |
| Activar extensiones RC6.0 | ❌ | ✅ |
| Modificar la Baseline RC5.5 | ❌ | ✅ (con revisión) |

## Cómo actualizar el sistema (usuarios)

**Usa únicamente:** `ACTUALIZAR_CLIENTE.bat`

1. Cierra el sistema PARAGUASMJ si está abierto
2. Haz doble clic en `ACTUALIZAR_CLIENTE.bat`
3. Espera a que termine (verás "ACTUALIZACIÓN COMPLETADA")
4. Reinicia el sistema

> **Importante:** Este script SOLO descarga actualizaciones. No puede
> subir cambios al repositorio ni modificar el código fuente.

## ¿Qué pasa con mis datos?

- Los datos (documentos, suscriptores, PQRS) están en la base de datos **local**
- La base de datos NO se borra al actualizar
- Si algo sale mal, el script hace un backup automático antes de actualizar

## Contraseñas y acceso

- La contraseña del administrador por defecto es: `PARAGUASMJ2026`
- **Cámbiala** en el primer inicio: Configuración → Usuarios → admin → Cambiar contraseña
- Usa contraseñas de al menos 10 caracteres con letras y números

## Documentos y firma OTP

El sistema usa **OTP por WhatsApp** para autorizar documentos:

1. El sistema envía un código de 6 dígitos al WhatsApp del firmante
2. El firmante ingresa el código en el sistema
3. El documento queda firmado con registro inmutable

> El código OTP expira en **30 minutos**. Si expira, solicita uno nuevo.

## Preguntas frecuentes

**¿Puedo instalar PARAGUASMJ en varios computadores?**
Sí. Cada instalación tiene su propia base de datos local. Para compartir
datos entre equipos, contacta al administrador técnico.

**¿Funciona sin internet?**
Sí, completamente. Internet solo es necesario para:
- Enviar OTP por WhatsApp (requiere internet)
- Actualizar el sistema (requiere internet)

**¿Qué hago si el sistema no arranca?**
1. Ejecuta `INICIAR.bat` (no el `.exe` directamente)
2. Si sigue sin arrancar, revisa `logs/` para ver el error
3. Contacta al administrador: zidmauricio-droid@github.com

## Seguridad de la información

- Toda la información está cifrada con HMAC-SHA256
- Los documentos tienen huella digital inmutable
- El log de auditoría no puede ser alterado
- Los respaldos se guardan automáticamente cada día en `database/backups/`
