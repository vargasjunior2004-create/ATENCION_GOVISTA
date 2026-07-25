# SaleStracker — Planilla de Ventas Diaria

Sistema web para registro y control de ventas diarias de telecomunicaciones FTTH.

## Stack

- **Backend:** Node.js + Express + SQLite (Sequelize ORM)
- **Frontend:** React 18
- **Auth:** JWT (roles: admin, ventas)
- **PDF:** pdfkit
- **Envío WhatsApp:** wa.me (link con mensaje prellenado)

## Inicio rápido

```bash
# Instalar dependencias
cd backend && npm install
cd ../frontend && npm install && cd ..

# Compilar frontend
cd frontend && npm run build && cd ..

# Crear directorio de datos
mkdir -p backend/data

# Iniciar (desarrollo)
cd backend && npm run dev

# Iniciar (producción — sirve frontend + backend en el mismo puerto)
cd backend && npm start
```

El admin por defecto es: `admin@salestracker.com` / `admin123`

Los 7 planes se crean automáticamente al iniciar por primera vez.

## Estructura

```
SalesTracker/
├── backend/
│   ├── src/
│   │   ├── config/database.js    # Conexión SQLite + Sequelize
│   │   ├── models/               # Plan, User, Sale
│   │   ├── routes/               # auth, plans, sales, users, reports
│   │   ├── middleware/auth.js     # JWT + roles
│   │   └── index.js              # Entry point + seed
│   └── data/                     # Archivo .sqlite (ignorado por git)
├── frontend/
│   └── src/
│       ├── components/           # Login, Layout, Dashboard, SaleForm, SalesList, PlansModule, UsersModule
│       ├── context/AuthContext.js
│       └── services/api.js
└── run.sh
```

## Modelo de datos

| plans         | sales               | users         |
|---------------|---------------------|---------------|
| code          | date                | name          |
| label         | clientCode          | email         |
| type          | clientName          | passwordHash  |
| speed (Mbps)  | serviceType         | role          |
| monthly       | planId (FK)         | active        |
| installation  | total (calculado)   |               |
| total         | createdBy (FK)      |               |
| active        | lastEditedBy (FK)   |               |
|               | lastEditedAt        |               |

**Regla de negocio:** El `total` de cada venta **siempre** se calcula del lado del servidor a partir del plan, nunca se acepta del frontend.

## Hosting

SQLite almacena datos en un archivo. **El hosting necesita disco persistente** — en Render free tier / Railway free tier el filesystem es efímero y el archivo se pierde en cada deploy.

Opciones:
- Usar un servicio con disco persistente (Render paid, Railway paid, DigitalOcean, etc.)
- Migrar a PostgreSQL (requiere cambios en `database.js` y `package.json`)

## API

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | /api/auth/login | No | Login |
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
| GET | /api/reports/pdf | Sí | Generar PDF planilla |
| GET | /api/reports/pdf-link | Sí | Obtener link público de descarga (1h) |
| GET | /api/reports/pdf-public | No | Descargar PDF con firma |
