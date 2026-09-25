# GO VISTA — Planilla de Movimientos

Sistema web para registro y control de movimientos diarios de telecomunicaciones FTTH (GO VISTA, Cobija — Bolivia).

**Produccion:** https://atencion-govista-2.onrender.com

## Stack

- **Backend:** Django 5 + Django REST Framework + PostgreSQL (Supabase)
- **Frontend:** React 18 + Tailwind CSS
- **Auth:** JWT (roles: admin, ventas)
- **Hosting:** Render (free tier)
- **Reportes:** PDF (reportlab), XLSX (openpyxl), PNG (Pillow)

> **Arranque limpio:** Al iniciar por primera vez se cargan 34 planes (fixture) y 2 usuarios (seed).
> No hay movimientos previos.

## Credenciales de acceso

Login por **nombre de usuario** (no email):

| Usuario | Rol | Contrasena |
|---------|-----|------------|
| Administrador | ADMINISTRADOR | `admin123` |
| JUNIOR | ADMINISTRADOR | `admin123` |

## Funcionalidades

### Movimientos

- **Registro:** formulario con auto-complete, fecha automatica (Bolivia UTC-4), campos en mayusculas
- **Tipos de movimiento:**
  - Nuevo Contrato — instala un plan nuevo con costo de instalacion + mensualidad
  - Cambio de Plan — migra a otro plan, cobra solo mensualidad (sin instalacion). Requiere seleccionar plan anterior
  - Recontratacion — reactiva un servicio con costo de instalacion + mensualidad
  - Retiro — solo cobra mensualidad (sin instalacion). Plan anterior disponible
  - Adicion — agrega servicio adicional (internet o TV), cobra solo mensualidad (sin instalacion). Solo muestra planes combo
  - Otro — tipo no clasificado
- **Tipo de adicion:** cuando se selecciona Adicion, se debe indicar sub-tipo: Adicion Internet o Adicion TV
- **Cambio de Plan:** dos selects de planes:
  - **Plan Anterior:** muestra todos los planes (activos + legacy) del tipo de servicio seleccionado
  - **Plan Nuevo:** muestra solo planes activos no legacy del tipo de servicio seleccionado
  - Solo cobra la mensualidad del plan nuevo, sin costo de instalacion
- **Montos calculados automaticamente** segun tipo de movimiento:

| Tipo | Instalacion | Total |
|------|-------------|-------|
| Nuevo Contrato | costos del plan | mensual + instalacion |
| Cambio de Plan | 0 | solo mensualidad |
| Recontratacion | costos del plan | mensual + instalacion |
| Retiro | 0 | solo mensualidad |
| Adicion | 0 | solo mensualidad |

- **Promociones:** modalidad de precio (normal o promocional) al registrar o editar un movimiento
- **Vista previa:** confirmacion antes de guardar
- **Edicion:** admin puede editar cualquier movimiento (incluye plan anterior, tipo de adicion)
- **Eliminacion:** admin puede eliminar con confirmacion ("Movimiento eliminado correctamente.")

### Filtros de Busqueda

- **Selects con opciones predeterminadas:**
  - Tipo de Movimiento: `-- Seleccione --`, `Todos los movimientos`, Nuevo Contrato, Cambio de Plan, Recontratacion, Retiro, Adicion, Otro
  - Tipo de Servicio: `-- Seleccione --`, `Todos los tipos de servicio`, Internet, TV Cable, TV Digital, Internet + TV Analoga, Internet + TV Digital
  - Formato: `-- Seleccione --`, PDF, Excel
- **Boton Buscar:** solo busca al hacer clic (no automatico)
- **Mensaje profesional:** cuando los selects estan en `-- Seleccione --` se muestra "Selecciona filtros para mostrar informacion"
- **Reporte condicionado:** boton deshabilitado (gris) hasta seleccionar los 3 filtros (movimiento, servicio y formato)

### Reportes (normalizados)

- **Formato desde filtros:** usuario elige PDF o Excel antes de generar
- **Columnas unificadas:** todos los reportes tienen las mismas 8 columnas:
  - FECHA | KARDEX | CLIENTE | SERVICIO | SOLICITUD | PLAN | MONTO | OPERADOR
- **Fecha:** formato DD/MM/YYYY en titulo y datos
- **Solicitud:**
  - Adicion muestra "ADICION INTERNET" o "ADICION TV" segun sub-tipo
  - Los demas muestran el label estandar (INSTALACIONES, CAMBIO DE PLAN, etc.)
- **Plan:**
  - Cambio de Plan muestra "PLAN ANTERIOR → PLAN NUEVO" en la columna PLAN
  - Los demas muestran el nombre del plan
- **Titulo PDF:** `MOV. CLIENTES — TIPO MOVIMIENTO — TIPO SERVICIO` + fechas
- **Links publicos:** PDF y XLSX con vigencia de 1 hora

### Promociones

- **CRUD completo** (solo admin):
  - Crear promocion: nombre, plan asociado (solo activos, no legacy), precio promocional de instalacion y/o mensualidad, vigencia (fecha inicio/fin)
  - Editar promocion
  - Activar/desactivar promocion
  - Eliminar promocion
- **Seleccion de precio:** al registrar un movimiento, si el plan tiene promociones vigentes, aparecen dos opciones:
  - Precio normal (costo estandar del plan)
  - Precio promocional (precio especial de la promocion seleccionada)
- **Restricciones:** solo se pueden crear promociones para planes activos y no legacy

### Dashboard

- Resumen diario con botones PDF, Excel y Foto
- Botones deshabilitados cuando no hay registros del dia
- Estadisticas: movimientos, instalaciones (nuevo contrato + recontratacion), retiros (hoy, semana, mes)

### Planes

- Busqueda por codigo/nombre/tipo
- Inhabilitar como actual (legacy) — no aparecen en selects de nuevos movimientos pero si en Plan Anterior para cambio de plan y retiros
- Eliminacion con confirmacion

### Usuarios

- Crear, editar, activar/desactivar, eliminar
- Notificaciones de exito al crear o editar usuario
- Admin no puede eliminarse a si mismo

### Sesion

- JWT 5 min + inactividad 5 min (solo clicks)
- Auto-logout en 401
- Paginacion: 25 registros por pagina
- **Menu de usuario:** dropdown con opciones "Cambiar Contrasena" y "Cerrar Sesion"
- **Cambiar Contrasena:** modal con contrasena actual, nueva contrasena y confirmacion

## Roles

- **ADMINISTRADOR:** acceso total (crear, editar, eliminar movimientos, planes, usuarios, promociones)
- **OPERADOR:** solo puede registrar movimientos y ver reportes

## Estructura

```
Sales_Tracker/
├── manage.py
├── salestracker/             # settings, urls, wsgi
├── core/
│   ├── models.py             # User, Plan, Promotion, Sale, Customer, Backup
│   ├── serializers.py
│   ├── views.py              # auth, plans, promotions, sales, users, dashboard
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
| POST | /api/auth/change-password | Si | Cambiar contrasena |
| GET | /api/plans | Admin | Listar planes |
| GET | /api/plans/active | Si | Planes activos (incluye campo legacy) |
| POST | /api/plans | Admin | Crear plan |
| PUT | /api/plans/:id | Admin | Editar plan |
| DELETE | /api/plans/:id | Admin | Eliminar plan |
| GET | /api/promotions | Admin | Listar promociones |
| GET | /api/promotions/active | Si | Promociones vigentes (planes activos, no legacy) |
| POST | /api/promotions | Admin | Crear promocion |
| PUT | /api/promotions/:id | Admin | Editar/activar/desactivar promocion |
| DELETE | /api/promotions/:id | Admin | Eliminar promocion |
| GET | /api/sales?from=&to=&requestType=&serviceType=&page=&page_size= | Si | Movimientos (paginado, 25/pag) |
| POST | /api/sales | Si | Crear movimiento |
| PUT | /api/sales/:id | Admin | Editar movimiento |
| DELETE | /api/sales/:id | Admin | Eliminar movimiento |
| GET | /api/dashboard/stats | Si | Estadisticas del dashboard |
| GET | /api/users | Admin | Listar usuarios |
| POST | /api/users | Admin | Crear usuario |
| PUT | /api/users/:id | Admin | Editar usuario |
| DELETE | /api/users/:id | Admin | Eliminar usuario |
| GET | /api/reports/pdf?from=&to=&requestType=&serviceType= | Si | PDF planilla |
| GET | /api/reports/xlsx?from=&to=&requestType=&serviceType= | Si | XLSX planilla |
| GET | /api/reports/png?from=&to=&requestType=&serviceType= | Si | PNG imagen del reporte |
| GET | /api/reports/pdf-link?from=&to=&requestType=&serviceType= | Si | Link publico PDF (1h) |
| GET | /api/reports/xlsx-link?from=&to=&requestType=&serviceType= | Si | Link publico XLSX (1h) |

## Despliegue en Render

- **Hosting:** Render free tier (512MB RAM, 0.1 CPU, 750 hrs/mes)
- **Database:** Supabase PostgreSQL (pooler endpoint, IPv4)
- **Estaticos:** WhiteNoise sirve archivos desde `staticfiles/`
- **Build:** `build.sh` ejecuta `collectstatic`
- **Inicio:** `gunicorn salestracker.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 60`

### Variables de entorno en Render

- `DATABASE_URL` — connection pooler de Supabase (puerto 6543)
- `DJANGO_SECRET_KEY` — clave secreta
- `DJANGO_DEBUG` — `false` en produccion
- `DJANGO_ALLOWED_HOSTS` — `*.onrender.com`

### Notas

- `frontend_build/` y `staticfiles/` van committeados (archivos servidos por WhiteNoise)
- `wsgi.py` ejecuta migraciones + seed automaticamente si no hay datos
- Pooler de Supabase usa IPv4, compatible con Render free tier
- Planes legacy no aparecen en el select al registrar nuevos movimientos
- Planes legacy si aparecen en el select de Plan Anterior (cambio de plan y retiro)
- Admin no puede eliminarse a si mismo
- 2 workers + 2 threads permite atender usuarios concurrentes (mientras uno genera PDF, otro hace consultas)
- Filtros de busqueda requieren seleccion explicita (no automatico)
- PDF solo se genera cuando ambos filtros estan seleccionados
- Cambio de plan y adicion solo cobran mensualidad (sin costo de instalacion)
- Retiro usa la mensualidad del plan como monto
- Dashboard cuenta recontratacion junto con nuevo contrato como instalaciones
