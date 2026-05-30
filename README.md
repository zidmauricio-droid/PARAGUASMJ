# PARAGUASMJ
## Sistema Integrado de Gestion Documental

**Asociacion de Suscriptores del Acueducto Comunitario El Puente**
Villeta, Cundinamarca, Colombia — NIT 832.001.389-2

---

### Descripcion
Sistema local de gestion documental institucional para acueducto comunitario rural.
Funciona 100% offline. Tecnologia: Python + Flask + SQLite.

### Instalacion rapida

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Inicializar base de datos
python database/inicializar_db.py

# 3. Ejecutar sistema
python run.py
```

Abre el navegador en `http://127.0.0.1:5000`
Credenciales iniciales: `admin` / `PARAGUASMJ2026`

### Modulos del sistema
- Registro central documental con consecutivos por area
- PQRS con alertas de vencimiento
- Comunicaciones oficiales (CAR, SSPD, Alcaldia)
- Proyectos comunitarios
- Balance hidrico e indicadores CRA (IANC, IRAC)
- GIS con Leaflet offline (5 zonas de prestacion)
- Firmas digitales via OTP WhatsApp (CallMeBot)
- Exportacion PDF (ReportLab) y Excel institucional
- Backups automaticos
- Scheduler de notificaciones (APScheduler)

### Estructura de consecutivos
`{AREA}-{TIPO}-{ANO}-{NNN}`
Ejemplo: `GA-OFI-2026-001`

### Soporte tecnico
Codigo core: M. Jimenez Ch.
Correo institucional: aacueductoelpuente@yahoo.com
