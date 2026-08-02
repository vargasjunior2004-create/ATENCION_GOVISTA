# SaleStracker — Planilla de Ventas Diaria

Sistema web para registro y control de ventas diarias de telecomunicaciones FTTH.

## Stack

- **Backend:** Django + Django REST Framework + SQLite
- **Frontend:** React 18 + Tailwind CSS
- **Auth:** JWT (roles: admin, ventas)
- **PDF:** reportlab
- **XLSX:** openpyxl
- **Envío WhatsApp:** wa.me (link con mensaje prellenado)

> Los datos son **mock**: se cargan con un comando de seed (usuarios, 7 planes,
> 30 ventas y arqueos de caja). Todo funciona de forma local sin configuración.

## Inicio rápido

```bash
# Instalar dependencias del backend
pip3 install --break-system-packages -r requirements.txt

# Instalar y compilar el frontend
cd frontend && npm install && npm run build && cd ..

# Preparar frontend servido por Django y base de datos mock
rm -rf frontend_build && cp -r frontend/build frontend_build
python3 manage.py migrate && python3 manage.py seed --force

# Iniciar (producción — sirve frontend + backend en el mismo puerto)
python3 manage.py runserver 0.0.0.0:4000
```

O simplemente ejecutar `./run.sh` que hace todo el proceso.

### Credenciales de acceso (mock)

El login del frontend es **solo por contraseña** (única por usuario):

| Usuario | Rol | Contraseña |
|---------|-----|------------|
| admin@salestracker.com | admin | `admin123` |
| juan@salestracker.com | ventas | `juan2026` |
| maria@salestracker.com | ventas | `maria2026` |

## Estructura

```
SalesTracker/
├── manage.py                 # Django en la raíz (estructura compatible con Wasmer Edge)
├── salestracker/             # settings, urls, wsgi
├── core/
│   ├── models.py             # User, Plan, Sale, CashCount, Outflow
│   ├── serializers.py
│   ├── views.py              # auth, plans, sales, users, cash-count
│   ├── report_views.py       # PDF/XLSX + links públicos firmados
│   ├── reports.py            # generación de PDF y XLSX
│   ├── auth.py               # JWT contra core.User
│   └── management/commands/seed.py   # datos mock
├── data/                     # db.sqlite3 (ignorado por git)
├── frontend_build/           # build del frontend (servido por Django, va a git)
├── frontend/                 # código fuente React
├── app.yaml                  # config de despliegue Wasmer Edge
├── pyproject.toml            # deps del backend (uv / Wasmer)
├── requirements.txt
└── run.sh
```

## Modelo de datos

| plans         | sales               | users         | cash_count / outflows |
|---------------|---------------------|---------------|------------------------|
| code          | date                | name          | date                  |
| label         | clientCode          | email         | conteo por denominación |
| type          | clientName          | passwordHash  | personName, amount, concept |
| speed (Mbps)  | serviceType         | role          | createdBy              |
| monthly       | planId (FK)         | active        |                        |
| installation  | total (calculado)   |               |                        |
| total         | createdBy (FK)      |               |                        |
| active        | lastEditedBy (FK)   |               |                        |
|               | lastEditedAt        |               |                        |

**Regla de negocio:** El `total` de cada venta **siempre** se calcula del lado del servidor a partir del plan, nunca se acepta del frontend.

## Datos mock

- 3 usuarios (1 admin, 2 ventas).
- 7 planes (internet, tv, combo) con precios en Bs.
- 30 ventas distribuidas en los últimos 14 días (para que el dashboard muestre datos).
- Arqueos de caja y salidas de efectivo para la fecha actual.

Recarga/regenera los datos con: `python3 manage.py seed --force`

## API

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | /api/auth/login | No | Login por contraseña (mock) |
| GET | /api/auth/me | Sí | Usuario actual |
| GET | /api/plans | Admin | Listar todos los planes |
| GET | /api/plans/active | Sí | Planes activos |
| POST | /api/plans | Admin | Crear plan |
| PUT | /api/plans/:id | Admin | Editar/inhabilitar plan |
| GET | /api/sales?from=&to= | Sí | Listar ventas por fecha |
| POST | /api/sales | Sí | Crear venta (total calculado en servidor) |
| PUT | /api/sales/:id | Admin | Editar venta |
| GET | /api/users | Admin | Listar usuarios |
| POST | /api/users | Admin | Crear usuario |
| PUT | /api/users/:id | Admin | Editar usuario |
| GET | /api/cash-count?date= | Sí | Arqueo de caja + salidas |
| POST | /api/cash-count | Sí | Guardar conteo |
| POST | /api/cash-count/outflows | Sí | Agregar salida |
| DELETE | /api/cash-count/outflows/:id | Sí | Eliminar salida |
| GET | /api/reports/pdf?from=&to= | Sí | Generar PDF planilla |
| GET | /api/reports/xlsx?from=&to= | Sí | Generar XLSX planilla |
| GET | /api/reports/pdf-link?from=&to= | Sí | Link público de descarga (1h) |
| GET | /api/reports/xlsx-link?from=&to= | Sí | Link público de descarga (1h) |
| GET | /api/reports/pdf-public/?token= | No | Descargar PDF con firma |
| GET | /api/cash-count/pdf?date= | Sí | PDF arqueo de caja |
| GET | /api/cash-count/pdf-link?date= | Sí | Link público arqueo (1h) |

## Despliegue en Wasmer Edge

El repo está preparado para [Wasmer Edge](https://wasmer.io) (plan gratuito): Django corre
como WSGI, el SQLite vive en un **volumen persistente** montado en `/data` y las migraciones +
seed corren solas en el primer arranque (`salestracker/wsgi.py`).

Pasos:

1. Crea una cuenta en https://wasmer.io y sube este repo a GitHub.
2. En `app.yaml`, reemplaza `TU_USUARIO` (owner y package) por tu nombre de usuario de Wasmer.
3. En el dashboard de Wasmer: crea una app Django y conéctala a tu repo de GitHub
   (rama `main`).
4. Guarda y despliega. La URL será `https://salestracker.wasmer.app`.

Notas:
- `frontend_build/` va committeado a git (es el frontend compilado que sirve Django).
- El volumen `data` persiste la BD; **no cambies su nombre** o se borra todo.
- `scaling.mode: single_concurrency` está activo porque SQLite admite un solo escritor.
- Cada deploy corre `migrate` + `seed` al arrancar (idempotente: el seed solo corre si no hay datos).
- Los datos del arqueo y las ventas se guardan en la BD del volumen. Los PDF/XLSX y el login funcionan igual que en local.

### Alternativas

- VPS propio con disco persistente: `./run.sh` y listo (SQLite en `data/db.sqlite3`).
- Para mayor escala: migrar a PostgreSQL cambiando `DATABASES` en `salestracker/settings.py`.
