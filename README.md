# GO VISTA — Movimiento de Clientes

Sistema web para registro y control de ventas diarias de telecomunicaciones FTTH (GO VISTA, Bolivia).

**Produccion:** https://atencion-govista-2.onrender.com

## Stack

- **Backend:** Django 5 + Django REST Framework + PostgreSQL (Supabase)
- **Frontend:** React 18 + Tailwind CSS
- **Auth:** JWT (roles: admin, ventas)
- **Hosting:** Render (free tier)
- **Reportes:** PDF (reportlab), XLSX (openpyxl), PNG (Pillow)
- **Envio WhatsApp:** wa.me (link con mensaje prellenado)

> **Arranque limpio:** Al iniciar por primera vez se cargan 34 planes (fixture) y 4 usuarios
> (seed). No hay ventas ni arqueos previos.

## Credenciales de acceso

Login por **nombre de usuario** (no email):

| Usuario | Rol | Contrasena |
|---------|-----|------------|
| Administrador | admin | `admin123` |
| JUNIOR | admin | `admin123` |
| Juan Perez | ventas | `juan2026` |
| Maria Rojas | ventas | `maria2026` |

## Funcionalidades

- **Alta de ventas:** formulario con auto-complete, fecha automatica (Bolivia UTC-4), campos en mayusculas
- **Reportes PDF:** tabla con 8 columnas, sin fila TOTAL
- **Reportes XLSX:** 14 columnas segun formato de empresa
- **Foto PNG:** imagen del reporte diario para compartir por WhatsApp
- **Arqueo de caja:** conteo por denominacion + salidas de efectivo
- **Paginacion:** 25 registros por pagina en listados
- **Sesion segura:** JWT 5 min + inactividad 5 min (solo clicks), auto-logout en 401
- **Dashboard:** resumen diario con botones PDF, Excel y Foto
- **Retiro:** registro con motivo y comentario, reporte PDF con columna "Motivo"

## Estructura

```
Sales_Tracker/
├── manage.py
├── salestracker/             # settings, urls, wsgi
├── core/
│   ├── models.py             # User, Plan, Sale, CashCount, Outflow, Customer
│   ├── serializers.py
│   ├── views.py              # auth, plans, sales, users, cash-count
│   ├── report_views.py       # PDF/XLSX/PNG + links publicos
│   ├── reports.py            # generacion de PDF, XLSX y PNG
│   ├── auth.py               # JWT contra core.User
│   ├── fixtures/planes.json  # 34 planes
│   └── management/commands/
│       ├── seed.py           # usuarios
│       └── import_excel.py   # importa catalogo desde Excel
├── frontend_build/           # build del frontend (servido por Django)
├── frontend/                 # codigo fuente React
├── staticfiles/              # archivos estaticos (WhiteNoise)
├── build.sh                  # build script Render
├── render.yaml               # config Render
├── requirements.txt
└── run.sh
```

## API

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| POST | /api/auth/login | No | Login por nombre |
| GET | /api/auth/me | Si | Usuario actual |
| GET | /api/plans | Admin | Listar planes |
| GET | /api/plans/active | Si | Planes activos |
| POST | /api/plans | Admin | Crear plan |
| PUT | /api/plans/:id | Admin | Editar plan |
| GET | /api/sales?from=&to=&page=&page_size= | Si | Ventas (paginado, 25/pag) |
| POST | /api/sales | Si | Crear venta |
| PUT | /api/sales/:id | Admin | Editar venta |
| GET | /api/users | Admin | Listar usuarios |
| POST | /api/users | Admin | Crear usuario |
| PUT | /api/users/:id | Admin | Editar usuario |
| GET | /api/cash-count?date= | Si | Arqueo de caja |
| POST | /api/cash-count | Si | Guardar conteo |
| POST | /api/cash-count/outflows | Si | Agregar salida |
| DELETE | /api/cash-count/outflows/:id | Si | Eliminar salida |
| GET | /api/reports/pdf?from=&to= | Si | PDF planilla |
| GET | /api/reports/xlsx?from=&to= | Si | XLSX planilla |
| GET | /api/reports/png?from=&to= | Si | PNG imagen del reporte |
| GET | /api/reports/pdf-link?from=&to= | Si | Link publico PDF (1h) |
| GET | /api/reports/xlsx-link?from=&to= | Si | Link publico XLSX (1h) |
| GET | /api/cash-count/pdf?date= | Si | PDF arqueo de caja |

## Despliegue en Render

- **Hosting:** Render free tier (512MB RAM, 0.1 CPU, 750 hrs/mes)
- **Database:** Supabase PostgreSQL (pooler endpoint, IPv4)
- **Estaticos:** WhiteNoise sirve archivos desde `staticfiles/`
- **Build:** `build.sh` ejecuta `collectstatic`
- **Inicio:** `gunicorn salestracker.wsgi:application --bind 0.0.0.0:$PORT`

### Variables de entorno en Render

- `DATABASE_URL` — connection pooler de Supabase (puerto 6543)
- `DJANGO_SECRET_KEY` — clave secreta
- `DJANGO_DEBUG` — `false` en produccion
- `DJANGO_ALLOWED_HOSTS` — `*.onrender.com`

### Notas

- `frontend_build/` y `staticfiles/` van committeados (archivos servidos por WhiteNoise)
- `wsgi.py` ejecuta migraciones + seed automaticamente si no hay datos
- Pooler de Supabase usa IPv4, compatible con Render free tier
