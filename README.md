# PARAGUASMJ

**Sistema de Gestión para Acueductos Rurales de Colombia**

> Herramienta 100% gratuita, open source y offline-first para que los acueductos rurales colombianos cumplan con la normativa (Ley 142/1994, CRA, SSPD, CAR) y evolucionen en su gestión documental, financiera y operativa.

---

## ¿Qué es PARAGUASMJ?

En muchas veredas de Colombia los acueductos comunitarios son manejados **con las manos y el corazón** pero con pocos conocimientos de las exigencias normativas. PARAGUASMJ cambia eso: un sistema local, sin internet obligatorio después de la instalación, sin costos de licencias, que corre en cualquier computador con 4GB de RAM.

**Acueducto piloto:** ASUACAP — Centro Poblado El Puente, Villeta, Cundinamarca.

---

## Módulos disponibles

| Módulo | Estado | Descripción |
|--------|--------|-------------|
| Documentos | ✅ Completo | Editor TipTap, 44 tipos, plantillas institucionales, PDF con membrete, firmas OTP |
| PQRS | ✅ Completo | Flujo completo Ley 142, exportación SUI/SSPD, órdenes de trabajo |
| Balance Hídrico | ✅ Completo | IANC, IUS CRA 906/2019, reportes FC01/FC15 para SSPD |
| GIS | ✅ Completo | Mapa Leaflet, infraestructura, fallas georreferenciadas |
| Proyectos | ✅ Completo | Gantt (Frappe), costos, evidencias SHA256, API REST |
| Convenios | ✅ Completo | Contratos, adiciones, prórrogas |
| Finanzas | ✅ Funcional | Bancos, caja, movimientos, libro bancario |
| Emergencias PEC | ✅ Completo | Riesgos, alertas, niveles quebrada |
| Reportes | ✅ Completo | CAR, SSPD, normativa colombiana |
| IA (opcional) | ✅ Proxy | Claude Haiku — funciona sin API key |
| Calidad Agua | 🔄 Parcial | Tablas listas, UI pendiente |
| Compras/Activos | 🔄 Parcial | Tablas listas, UI pendiente |

---

## Stack tecnológico (100% gratuito)

| Capa | Tecnología | Licencia |
|------|-----------|---------|
| Backend | Flask 3.1 + Waitress | BSD |
| Base de datos | SQLite 3 WAL | Dominio público |
| Frontend | Bootstrap 5.3 + Jinja2 | MIT |
| Editor | TipTap 2.4 UMD | MIT |
| Mapas | Leaflet 1.9 | BSD |
| PDF | ReportLab 4.1 | BSD |
| Excel | OpenPyXL 3.1 | MIT |
| Gantt | Frappe Gantt | MIT |
| Scheduler | APScheduler 3.10 | MIT |

---

## Instalación rápida (Windows)

```bash
# 1. Descargar y descomprimir PARAGUASMJ_v10.zip
# 2. Doble clic en INSTALAR.bat
# 3. Doble clic en INICIAR.bat
# 4. Abrir http://127.0.0.1:5000
# Credenciales: admin / PARAGUASMJ2026
```

## Instalación para desarrollo

```bash
git clone https://github.com/TU_USUARIO/PARAGUASMJ.git
cd PARAGUASMJ
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus valores
python database/inicializar_db.py
python run.py
```

---

## Variables de entorno

Copiar `.env.example` a `.env` y configurar:

```bash
SECRET_KEY=clave_aleatoria_segura
ANTHROPIC_API_KEY=opcional_para_IA
WHATSAPP_API_KEY=opcional_para_alertas
EMAIL_USUARIO=opcional_para_notificaciones
```

---

## Estructura del proyecto

```
PARAGUASMJ/
├── app.py                 # Fábrica Flask (16 blueprints)
├── config.py              # Configuración central
├── run.py                 # Punto de entrada (Waitress)
├── routes/                # 16 módulos Flask
├── core/                  # 13 servicios (PDF, email, OTP, backup...)
├── templates/             # 36 templates Jinja2
├── static/                # CSS, JS, Leaflet
├── database/
│   └── inicializar_db.py  # 104 tablas, 69 índices
└── requirements.txt
```

---

## Normativa colombiana implementada

- Ley 142 de 1994 — Servicios Públicos Domiciliarios
- Resolución CRA 906/2019 — IUS (Índice Único de Servicio)
- Ley 373/1997 — PUEAA (Plan Uso Eficiente Agua)
- Resolución 330/2017 — Calidad del agua
- Resolución SSPD 54575/2015 — PQRS

---

## Contribuir

Este proyecto es para los acueductos rurales de Colombia. Si quieres contribuir:

1. Fork el repositorio
2. Crea una rama: `git checkout -b mejora/nombre-modulo`
3. Commit: `git commit -m "feat: descripción del cambio"`
4. Push: `git push origin mejora/nombre-modulo`
5. Pull Request

---

## Licencia

MIT — Libre para uso, modificación y distribución.

---

*Hecho con corazón para los acueductos comunitarios de Colombia.*
