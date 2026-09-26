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

### Copias de Seguridad

Respaldo **manual** de PostgreSQL. Solo administradores.

- Un solo boton: **Generar y Descargar** — no hay seleccion de fecha, tamano ni formato
- Usa `pg_dump` en formato custom (`.dump`), comprimido y restaurable con `pg_restore`
- Solo se respalda el esquema `public` (los esquemas internos de Supabase no se incluyen)
- El archivo viaja al navegador y **se elimina del servidor** al terminar la descarga
- En el historial queda solo metadata: fecha, operador, tamano, SHA-256, duracion y estado
- Integridad verificada: se calcula el SHA-256 al generar y se comprueba contra el archivo entregado
- No se puede generar un respaldo mientras otro esta en curso (restriccion en base de datos)
- Sin cifrado: el archivo contiene datos legibles

> **Recomendacion:** genera uno por mes y guardalo en la carpeta `GO_VISTA_BACKUPS`.
> Como no va cifrado, esa carpeta debe estar protegida y, si el equipo es Portatil,
> con BitLocker activado.

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
│       ├── import_excel.py   # importa catalogo desde Excel
│       └── backup_database.py # genera el respaldo (pg_dump / SQLite)
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
| GET | /api/health | No | Estado del servicio y de la base de datos |
| GET | /api/backups | Admin | Historial de respaldos (solo metadata) |
| POST | /api/backups | Admin | Genera el respaldo y lo descarga (409 si ya hay uno en curso) |
| DELETE | /api/backups/:id | Admin | Elimina el registro del historial |

## Despliegue en Render

- **Hosting:** Render free tier (512MB RAM, 0.1 CPU, 750 hrs/mes)
- **Database:** Supabase PostgreSQL 17.6
- **Estaticos:** WhiteNoise sirve archivos desde `staticfiles/`
- **Build:** `build.sh` instala `postgresql-client-17` (PGDG) y ejecuta `collectstatic`
- **Inicio:** `gunicorn salestracker.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 60`

### Variables de entorno en Render

- `DATABASE_URL` — coneccion de la app. Usa el **transaction pooler** (puerto 6543)
- `BACKUP_DATABASE_URL` — coneccion exclusiva de `pg_dump`. **Session pooler** (puerto 5432)
- `DJANGO_SECRET_KEY` — clave secreta
- `DJANGO_DEBUG` — `false` en produccion
- `DJANGO_ALLOWED_HOSTS` — `*.onrender.com`

> **Por que hacen falta dos conexiones:** el transaction pooler reparte cada
> sentencia entre distintas conexiones de PostgreSQL y no mantiene el estado de
> sesion. La app funciona bien asi, pero `pg_dump` necesita una sesion estable
> para el snapshot: contra el puerto 6543 falla de forma inconsistente. Por eso
> los respaldos usan su propia cadena en el puerto 5432.

> **Ojo con el usuario:** en el Session pooler el usuario no es `postgres`, sino
> `postgres.<project-ref>`. La contraseña es la misma de la app.

### Restaurar un respaldo

El `.dump` se genera en formato custom. Para restaurarlo:

```bash
# Crear una base vacia en el destino
createdb -h HOST -p 5432 -U postgres.<ref> restauracion

# Restaurar (--clean --if-exists es necesario: sin esto falla con
# "ya existe el esquema public")
pg_restore -h HOST -p 5432 -U postgres.<ref> -d restauracion \
  --clean --if-exists --no-owner --no-privileges respaldo.dump
```

Verifica el checksum antes de restaurar:

```bash
sha256sum respaldo.dump
```

Y comparalo con el campo `checksum` del historial en la app.

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
- Los respaldos son manuales: no hay scheduler automatico
- El `.dump` no va cifrado; en produccion solo existe en el servidor mientras se descarga
- Un respaldo pendiente de un proceso que muere queda en estado `running`: se puede borrar desde el historial
- `pg_dump` debe ser igual o mas nuevo que el servidor; `build.sh` instala la version 17 y el comando verifica la compatibilidad antes de respaldar
- El historial guarda metadata, nunca el archivo
- `core/tests.py` y `core/tests_full.py` cubren permisos, generacion, streaming, integridad, concurrencia y el ciclo `pg_dump` → `pg_restore`
