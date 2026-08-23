# GO VISTA — Movimiento de Clientes

Sistema web para registro y control de ventas diarias de telecomunicaciones FTTH (GO VISTA, Bolivia).

## Stack

- **Backend:** Django + Django REST Framework + SQLite
- **Frontend:** React 18 + Tailwind CSS
- **Auth:** JWT (roles: admin, ventas)
- **Reportes:** PDF (reportlab), XLSX (openpyxl), PNG (Pillow)
- **Envío WhatsApp:** wa.me (link con mensaje prellenado)

> **Arranque limpio:** Al iniciar por primera vez se cargan 33 planes (fixture) y 4 usuarios
> (seed). No hay ventas ni arqueos previos.

## Inicio rápido

```bash
# Instalar dependencias
pip3 install --break-system-packages -r requirements.txt

# Compilar frontend
cd frontend && npm install && npm run build && cd ..
rm -rf frontend_build && cp -r frontend/build frontend_build

# Base de datos
python3 manage.py migrate
python3 manage.py loaddata planes
python3 manage.py seed --users-only

# Iniciar (puerto 4000)
python3 manage.py runserver 0.0.0.0:4000
```

### Credenciales de acceso

Login por **nombre de usuario** (no email):

| Usuario | Rol | Contraseña |
|---------|-----|------------|
| Administrador | admin | `admin123` |
| junior | admin | `admin123` |
| Vendedor | ventas | `vendedor123` |
| lucas | ventas | `lucas123` |

## Funcionalidades

- **Alta de ventas:** formulario con auto-complete, fecha automática (Bolivia UTC-4), campos en mayúsculas
- **Reportes PDF:** tabla con 8 columnas, sin fila TOTAL
- **Reportes XLSX:** 14 columnas según formato de empresa
- **Foto PNG:** imagen del reporte diario para compartir por WhatsApp
- **Arqueo de caja:** conteo por denominación + salidas de efectivo
- **Paginación:** 25 registros por página en listados
- **Sesión segura:** JWT 3 min + inactividad 3 min (solo clicks), auto-logout en 401
- **Dashboard:** resumen diario con botones PDF, Excel y Foto

## Estructura

```
Sales_Tracker/
├── manage.py
├── salestracker/             # settings, urls, wsgi
├── core/
│   ├── models.py             # User, Plan, Sale, CashCount, Outflow
│   ├── serializers.py
│   ├── views.py              # auth, plans, sales, users, cash-count
│   ├── report_views.py       # PDF/XLSX/PNG + links públicos
│   ├── reports.py            # generación de PDF, XLSX y PNG
│   ├── auth.py               # JWT contra core.User
│   ├── fixtures/planes.json  # 33 planes
│   └── management/commands/
│       ├── seed.py           # usuarios
│       └── import_excel.py   # importa catálogo desde Excel
├── data/                     # db.sqlite3
├── frontend_build/           # build del frontend (servido por Django)
├── frontend/                 # código fuente React
├── app.yaml                  # config Wasmer Edge
├── requirements.txt
└── run.sh
```

## API

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | /api/auth/login | No | Login por nombre |
| GET | /api/auth/me | Sí | Usuario actual |
| GET | /api/plans | Admin | Listar planes |
| GET | /api/plans/active | Sí | Planes activos |
| POST | /api/plans | Admin | Crear plan |
| PUT | /api/plans/:id | Admin | Editar plan |
| GET | /api/sales?from=&to=&page=&page_size= | Sí | Ventas (paginado, 25/pág) |
| POST | /api/sales | Sí | Crear venta |
| PUT | /api/sales/:id | Admin | Editar venta |
| GET | /api/users | Admin | Listar usuarios |
| POST | /api/users | Admin | Crear usuario |
| PUT | /api/users/:id | Admin | Editar usuario |
| GET | /api/cash-count?date= | Sí | Arqueo de caja |
| POST | /api/cash-count | Sí | Guardar conteo |
| POST | /api/cash-count/outflows | Sí | Agregar salida |
| DELETE | /api/cash-count/outflows/:id | Sí | Eliminar salida |
| GET | /api/reports/pdf?from=&to= | Sí | PDF planilla |
| GET | /api/reports/xlsx?from=&to= | Sí | XLSX planilla |
| GET | /api/reports/png?from=&to= | Sí | PNG imagen del reporte |
| GET | /api/reports/pdf-link?from=&to= | Sí | Link público PDF (1h) |
| GET | /api/reports/xlsx-link?from=&to= | Sí | Link público XLSX (1h) |
| GET | /api/cash-count/pdf?date= | Sí | PDF arqueo de caja |

## Despliegue en Wasmer Edge

Django corre como WSGI, SQLite en volumen persistente `/data`, migraciones automáticas en `wsgi.py`.

### Pasos

1. Subir repo a GitHub.
2. En Wasmer: crear app conectada al repo (rama `main`).
3. Si hay deploy previo, **borrar volumen `data`**.
4. Desplegar.

### Dominio personalizado

1. Wasmer → Settings → Domains → Add dominio.
2. DNS: CNAME en modo **DNS only** (no proxy).
3. Wasmer → Refresh (HTTPS automático).

Notas:
- `frontend_build/` va committeado (frontend compilado servido por Django).
- Volumen `data` persiste la BD.
- `scaling.mode: single_concurrency` (SQLite un solo escritor).
