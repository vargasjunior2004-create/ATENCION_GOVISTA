# SaleStracker — Planilla de Ventas Diaria

Sistema web para registro y control de ventas diarias de telecomunicaciones FTTH.

## Stack

- **Backend:** Django + Django REST Framework + SQLite
- **Frontend:** React 18 + Tailwind CSS
- **Auth:** JWT (roles: admin, ventas)
- **PDF:** reportlab
- **XLSX:** openpyxl
- **Envío WhatsApp:** wa.me (link con mensaje prellenado)

> **Arranque limpio:** Al iniciar por primera vez se cargan 33 planes (fixture) y 3 usuarios
> (seed). No hay ventas ni arqueos previos. Todo funciona de forma local sin configuración.

## Inicio rápido

```bash
# Instalar dependencias del backend
pip3 install --break-system-packages -r requirements.txt

# Instalar y compilar el frontend
cd frontend && npm install && npm run build && cd ..

# Preparar frontend servido por Django y base de datos
rm -rf frontend_build && cp -r frontend/build frontend_build
python3 manage.py migrate
python3 manage.py loaddata planes      # 33 planes (1 legacy combo)
python3 manage.py seed --users-only    # 3 usuarios, sin ventas mock

# Iniciar
python3 manage.py runserver 0.0.0.0:4000
```

O simplemente ejecutar `./run.sh` que hace todo el proceso.

### Credenciales de acceso

El login del frontend es **solo por contraseña** (única por usuario):

| Usuario | Rol | Contraseña |
|---------|-----|------------|
| admin@salestracker.com | admin | `admin123` |
| juan@salestracker.com | ventas | `juan2026` |
| maria@salestracker.com | ventas | `maria2026` |

## Estructura

```
SalesTracker/
├── manage.py                 # Django en la raíz (compatible Wasmer Edge)
├── salestracker/             # settings, urls, wsgi
├── core/
│   ├── models.py             # User, Plan, Sale, CashCount, Outflow
│   ├── serializers.py
│   ├── views.py              # auth, plans, sales, users, cash-count
│   ├── report_views.py       # PDF/XLSX + links públicos firmados
│   ├── reports.py            # generación de PDF y XLSX
│   ├── auth.py               # JWT contra core.User
│   ├── fixtures/planes.json  # 33 planes (catálogo importado desde Excel)
│   └── management/commands/
│       ├── seed.py           # usuarios (users-only)
│       └── import_excel.py   # importa catálogo desde Excel
├── data/                     # db.sqlite3 (ignorado por git)
├── frontend_build/           # build del frontend (servido por Django, va a git)
├── frontend/                 # código fuente React (tema verde/white)
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
| monthly       | planId (FK)         | active        | created_at (hora)      |
| installation  | total (calculado)   |               |                        |
| total         | createdBy (FK)      |               |                        |
| active        | lastEditedBy (FK)   |               |                        |
| legacy        | lastEditedAt        |               |                        |

**Reglas de negocio:**
- El `total` de cada venta **siempre** se calcula del lado del servidor a partir del plan, nunca se acepta del frontend.
- Planes marcados como `legacy` solo pueden usarse en ventas de tipo `retiro` (validación en frontend).
- El arqueo de caja muestra **Efectivo Total = Total Contado + Total Salidas**.
- Cada salida de efectivo registra automáticamente la **hora** (`created_at`) de cuándo se registró.

## Arqueo de Caja

- **Conteo de efectivo:** monedas (0.50, 1, 2, 5 Bs) y billetes (10, 20, 50, 100, 200 Bs).
- **Salidas de efectivo:** registro de a quién se le dio el monto, concepto y hora exacta.
- **Efectivo Total:** suma del total contado + total salidas.
- **PDF:** incluye tabla de salidas con columna de hora (HH:MM).

## API

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | /api/auth/login | No | Login por contraseña |
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
| POST | /api/cash-count/outflows | Sí | Agregar salida (captura hora automática) |
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
como WSGI, el SQLite vive en un **volumen persistente** montado en `/data` y las migraciones
corren solas en el primer arranque (`salestracker/wsgi.py`).

### Bootstrap automático (wsgi.py)

Al arrancar en Wasmer (`WASMER=true`):
1. `python manage.py migrate`
2. Si no hay planes → `loaddata planes` (33 planes desde fixture)
3. Siempre → `seed --users-only` (crea usuarios si no existen)

**No se crean ventas mock.** La BD queda limpia: solo planes + usuarios.

### Pasos de despliegue

1. Crea una cuenta en https://wasmer.io y sube este repo a GitHub.
2. En Wasmer: crea la app (conecta al repo GitHub, rama `main`).
3. Si hay deploy previo, **borra el volumen `data`** para que arranque limpio.
4. Despliega. URL: `https://salestracker-vargasjunior2004-create.wasmer.app`.

### Dominio personalizado (`vistabolivia.qd.je`)

1. En Wasmer → Settings → Domains → Add `vistabolivia.qd.je`.
2. En DigitalPlat → fijar nameservers externos (ej: Cloudflare).
3. En Cloudflare: crear registro DNS (CNAME) en modo **DNS only**.
4. En Wasmer → Refresh (HTTPS automático).

Notas:
- `frontend_build/` va committeado a git (frontend compilado servido por Django).
- El volumen `data` persiste la BD; **no cambies su nombre** o se borra todo.
- `scaling.mode: single_concurrency` está activo porque SQLite admite un solo escritor.
- `.qd.je` no está en PSL → Cloudflare proxy naranja puede fallar; usar DNS only.
