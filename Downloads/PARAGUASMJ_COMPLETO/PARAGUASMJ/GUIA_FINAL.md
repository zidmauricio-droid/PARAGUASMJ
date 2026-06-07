# GUIA DE INSTALACION Y MANTENIMIENTO — PARAGUASMJ

## 1. Requisitos del sistema
- Windows 10/11 (64-bit)
- Python 3.11 o superior
- 4 GB de RAM minimo
- 500 MB de espacio en disco

## 2. Instalacion desde codigo fuente

1. Abra la terminal (cmd) en la carpeta `PARAGUASMJ_2026`
2. (Opcional) Cree entorno virtual:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
3. Instale dependencias:
   ```
   pip install -r requirements.txt
   ```
4. Inicialice la base de datos:
   ```
   python database/inicializar_db.py
   ```
5. Ejecute el sistema:
   ```
   python run.py
   ```
6. Abra el navegador en `http://127.0.0.1:5000`
7. Ingrese con `admin` / `PARAGUASMJ2026` (cambie la clave en el primer uso)

## 3. Configuracion inicial obligatoria

- Vaya a **Admin → Configuracion**
- En categoria **Institucional**: actualice nombre, NIT, representante legal
- En categoria **Notificaciones**: ingrese el API Key de WhatsApp (CallMeBot) si desea firmas OTP
- Suba el logo institucional (opcional) en formato base64

## 4. Funcionamiento offline

Para trabajar completamente sin internet:
- Descargue Leaflet desde https://leafletjs.com y coloque en `static/leaflet/`
- Descargue TinyMCE self-hosted desde https://tiny.cloud y coloque en `static/tinymce/`
- Los tiles del mapa de OpenStreetMap requieren internet; puede usar tiles locales con TileServer-GL

## 5. Generar ejecutable .exe

```
pip install pyinstaller
pyinstaller --clean build/asuacap_app.spec
```

El ejecutable quedara en `dist/PARAGUASMJ_Local.exe`

## 6. Solucion de problemas comunes

| Problema | Solucion |
|----------|----------|
| Error "database is locked" | Reinicie la aplicacion; solo debe estar corriendo una instancia |
| El mapa aparece gris | Descargue Leaflet local en static/leaflet/ |
| TinyMCE no aparece | Descargue TinyMCE en static/tinymce/ |
| Puerto 5000 ocupado | Cambie port=5001 en run.py |
| OTP no llega por WhatsApp | Verifique el API Key de CallMeBot en Configuracion |

## 7. Mantenimiento

- **Backups**: Se crean automaticamente cada dia a las 8 AM en `database/backups/`
- **Logs**: Se guardan en `logs/paraguasmj.log` con rotacion de 5 MB
- **Actualizaciones**: Reemplace archivos .py y .html, ejecute migraciones si cambia la BD

## 8. Soporte tecnico
- Codigo core: M. Jimenez Ch.
- Correo institucional ASUACAP: aacueductoelpuente@yahoo.com
