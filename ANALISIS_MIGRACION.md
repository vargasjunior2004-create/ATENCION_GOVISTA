# Análisis de Migración: ARCHIVO ATENCIÓN AL CLIENTE 2026.xlsx → Sales Tracker

**Fecha:** 2026-08-08
**Analista:** Arquitecto de Software (análisis automatizado + revisión)
**Fuente:** `ARCHIVO ATENCION AL CLIENTE 2026.xlsx`

---

## 1. Estructura de Datos

### 1.1 Hojas

El archivo tiene **10 hojas**: 2 de gráficos y 8 de datos.

| Hoja | Filas | Columnas | Propósito | Estado |
|---|---|---|---|---|
| `MOV. CLIENTES` | 3322 con datos (máx. 5858) | 17 | Registro principal de movimientos/ventas | ✅ Activa (2023-07 → 2025) |
| `CALIDAD SERVICIO TV CABLE` | 1 con datos (máx. 60053) | 15 | Encuestas de satisfacción TV | ⚠️ Template (1 fila muestra) |
| `CALIDAD SERVICIO INTERNET` | 1 con datos (máx. 12444) | 15 | Encuestas de satisfacción Internet | ⚠️ Template (1 fila muestra) |
| `QUEJAS` | 0 con datos | 22 | Seguimiento de quejas (hasta 3 por cliente) | ⚠️ Template vacío |
| `CAMBIOS DE SERVICIOS` | 0 con datos | 18 | Cambios de plan y su impacto monetario | ⚠️ Template vacío |
| `LISTAS` | 56 | 17 | Tablas de referencia para los desplegables | ✅ Activa |
| `Proyección de contratos` | 17 | 15 | Proyección mensual de ventas | ✅ Activa |
| `Hoja1` | 65 fechas | 2 | Calendario de días laborables | ⚠️ Auxiliar |
| `Gráfico1`, `Gráfico2` | — | — | Gráficos derivados de MOV. CLIENTES | ⚠️ Legado |

### 1.2 Columnas por hoja

**MOV. CLIENTES (hoja principal)** — fila 6 = encabezados:

| # | Columna | Tipo | Ejemplo | Obligatoria |
|---|---|---|---|---|
| A | FECHA | fecha | 2023-07-05 | ✅ |
| B | KARDEX | texto (código cliente) | `13316`, `20123-1` | ✅ |
| C | NOMBRE DEL CLIENTE | texto | PAUL ROGER NINA PEÑA | ✅ |
| D | TIPO DE SERVICIO | lista | INTERNET, TV ANALOGA, INTERNET + TV ANALOGA | ✅ |
| E | TIPO DE SOLICITUD | lista | NUEVO CONTRATO, CAMBIO DE PLAN, RETIRO, RECONTRATACION, ADICIÓN... | ✅ |
| F | PAQUETE TV CABLE | texto | SERVICIO BASICO 1, GOTV-120 | según servicio |
| G | PAQUETE INTERNET | texto | 30 M, GO-60(FEB25), GoBasic | según servicio |
| H | MONTO INICIAL | número (Bs) | 145 | ✅ |
| I | MOTIVO CAMBIO DE PLAN | lista | ECONÓMICOS, MAL SERVICIO... | solo en cambios |
| J | PAQUETE CAMBIO TV CABLE | texto | SERVICIO BASICO 2 | solo en cambios |
| K | PAQUETE CAMBIO INTERNET | texto | 25 M | solo en cambios |
| L | MONTO FINAL | número | 90 | solo en cambios |
| M | DIFERENCIA | número | 55 | calculable |
| N | CAJERA (O) | lista | YULCIDY RODRIGUEZ | ✅ |
| O | COMENTARIOS | texto libre | — | no |

**CALIDAD SERVICIO (TV e INTERNET):** `FECHA`, `CODIGO`, `NUMERO`, `MESA`, `OPERADOR`, `ESTADO`, `PREGUNTA`, `TIPO_RESPUESTA`, `RESPUESTA` (Muy Bueno/Bueno/Regular/Malo), `KARDEX`, `CELULAR`, `SUCURSAL`, `Mes`, `Semana`, `Puntaje`.

**QUEJAS (22 cols):** FECHA, KARDEX, CAJERA, MOTIVO DE RETIRO, y por queja (hasta 3): FECHA DE QUEJA, MOTIVO DE QUEJA, SOLUCIÓN DE QUEJA, TIEMPO QUEJA, TÉCNICO. + OBSERVACIÓN.

**CAMBIOS DE SERVICIOS (18 cols):** KARDEX, NOMBRE, BARRIO, TIPO DE SERVICIO ANTES, PLAN ANTES, SERVICIO ACTUAL, TIPO DE SERVICIO ACTUAL, FECHA DE CAMBIO, TIPO DE CAMBIO, CAJERO, MOTIVO DE CAMBIO, MES, AÑO, CUENTA, DIA, MENSUALIDAD ANTERIOR, MENSUALIDAD ACTUAL, MONTO EN CONTRA DE LA EMPRESA.

**LISTAS (referencia):** NOMBRE SERVICIO, SERVICIO, PAQUETE TV, PAQUETE INTERNET, TECNOLOGIA, BARRIO, TIPO, RESUMEN, CAJERA, LUGAR DE VENTA, MOTIVO RETIRO, TIPO DE CAMBIO, MOTIVO CAMBIO, NOMBRES, ESCARGADO, SISTEMA CLIENTE.

### 1.3 Relaciones / claves

- **KARDEX** es la clave natural del cliente. Aparece en MOV. CLIENTES, CALIDAD, QUEJAS y CAMBIOS. **No hay tabla maestra de clientes** → se repite el nombre en cada fila.
- **CAJERA** conecta con la lista de `LISTAS.CAJERA` y con los usuarios reales de la empresa.
- **PAQUETE / SERVICIO** conectan con `LISTAS.PAQUETE TV` y `LISTAS.PAQUETE INTERNET`.
- Las hojas QUEJAS y CAMBIOS referencian clientes por KARDEX, pero **no hay integridad referencial** (puede referirse un KARDEX inexistente).

### 1.4 Fórmulas

- **MOV. CLIENTES:** sin fórmulas (la columna DIFERENCIA se deja vacía; los totales son manuales).
- **CALIDAD SERVICIO:** `Mes = MONTH(FECHA)`, `Semana = WEEKNUM(FECHA)`, `Puntaje = IF(RESPUESTA="Muy Bueno",3, IF("Bueno",2, ...))`. O sea: hay datos derivados que en la app deben **calcularse solos**.
- **CAMBIOS DE SERVICIOS:** MES, AÑO, DIA se derivan de FECHA DE CAMBIO (manuales en Excel).
- **Gráfico1/2:** pivotes/gráficos sobre MOV. CLIENTES.

### 1.5 Validaciones de datos

| Hoja | Validación |
|---|---|
| MOV. CLIENTES | Fecha en col. A (rango A7:A1558, A1561:A2943); listas desplegables `INDIRECT("CAJERA[...]")` y `INDIRECT("MOTIVOCAMBIO[...]")` (rangos con nombre) |
| CAMBIOS DE SERVICIOS | Lista desplegable para TIPO DE CAMBIO (`$M$2:$M$28`) y MENSUALIDAD (`$M$2:$M$29`) |
| LISTAS | Fuente de las listas (datos + rangos con nombre) |

⚠️ Las validaciones **no cubren toda la columna** (solo hasta fila ~3289 de 5858), por lo que filas posteriores aceptan cualquier valor → una fuente de errores.

### 1.6 Formato condicional y macros

- **MOV. CLIENTES:** 5 reglas de formato condicional (resaltado, p.ej. por montos/tipos).
- **Macros/VBA:** no se detectaron en la revisión (sin módulos de código). Los gráficos son estáticos.

---

## 2. Procesos de Negocio

| Proceso | Cómo funciona en Excel | Rol que registra |
|---|---|---|
| **Venta / movimiento** | La cajera agrega una fila en MOV. CLIENTES: fecha, cliente (kardex+nombre), servicio, paquete, monto. Tipos: NUEVO CONTRATO, CAMBIO DE PLAN, RECONTRATACION, RETIRO, ADICIÓN, BAJA TEMPORAL. | Cajera |
| **Encuesta de satisfacción** | Datos importados (SOFTV/TopSAP) a las hojas CALIDAD; el operador atiende y el cliente califica. El Puntaje lo calcula Excel. | Operador / Call Center |
| **Quejas** | Se registra hasta 3 quejas por cliente con fecha, motivo, solución, tiempo y técnico. | Atención al Cliente |
| **Cambio de servicio** | Se registra el plan anterior vs. actual y el impacto (MONTO EN CONTRA DE LA EMPRESA). | Cajero / Encargado |
| **Proyección** | Mensual, manual: nuevos contratos, solo internet, solo TV, combos, adiciones, recontratación, traslados, extensiones. | Encargada Administración |
| **Reportes** | Manuales: los gráficos (Gráfico1/2) y exportaciones puntuales. Sin dashboard en vivo. | Administración |

**Roles detectados (LISTAS.NOMBRES / ESCARGADO):** CAJERA, ENCARGADA ADMINISTRACION, JEFATURA OFICINA, ENCARGADA LOGISTICA, MESA CONTROL, CALL CENTER, ATENCION AL CLIENTE, REVISION DE EQUIPOS Y MONITOREO, LIMPIEZA, TECNICO, COBRADOR, ENCARGADO CABECERA.

**Distribución real de movimientos (3322 filas):**
- NUEVO CONTRATO: 2494 · CAMBIO DE PLAN: 548 · RETIRO: 192 · RECONTRATACION: 55 · ADICIÓN INTERNET: 16 · ADICIÓN TV: 9 · BAJA TEMPORAL: 1
- SERVICIOS: INTERNET 2255 · INTERNET+TV ANALOGA 587 · TV ANALOGA 470 · TV DIGITAL 3 · INTERNET+TV DIGITAL 1
- 3135 KARDEX únicos en 3322 filas → ~5.6% de duplicados de cliente.
- Top cajeras: YULCIDY RODRIGUEZ (896), JONATAN ALVEZ (832), JUNIOR VILLARROEL (325)...

---

## 3. Limitaciones del Excel (observadas en datos)

- ❌ **Duplicados de cliente:** un mismo KARDEX aparece en varias filas; sin dirección/barrio/teléfono maestros.
- ❌ **Errores de tipeo:** `NUEVO COMTRATO` (typo), `YENNIFER MULLER` vs `YENIFER MULLER` (misma persona, 2 formas), KARDEX `13316` y `20123-1` para el mismo nombre.
- ❌ **Datos corruptos:** fecha `10/04/205` (año mal), montos negativos (`min=-145`), paquetes con nomenclatura inconsistente (`30 M` / `GO-60(FEB25)` / `GoBasic` — el mismo servicio).
- ❌ **Sin trazabilidad:** no se sabe quién editó ni cuándo; solo existe el valor final.
- ❌ **Acceso concurrente:** un solo archivo compartido → conflicto de edición.
- ❌ **Sin notificaciones:** no hay alertas de quejas vencidas ni seguimientos pendientes.
- ❌ **Reportes manuales:** los gráficos no se actualizan solos y no hay dashboard.
- ❌ **Integridad parcial:** validaciones que no cubren toda la columna; QUEJAS/CAMBIOS sin FK.
- ❌ **Información muerta:** hojas template de 60.000 filas pre-formateadas sin datos.
- ❌ **Sin integración en vivo** con SOFTV/TopSAP (las encuestas se importan manualmente).

---

## 4. Mapeo a Sales Tracker (Excel → App)

**Arquitectura actual de la app:** React (SPA, `frontend/`) + Django REST (`core/`) + SQLite. Endpoints en `core/urls.py`. Reportes PDF/XLSX con enlaces públicos firmados. Auth con roles `admin` / `ventas`.

**Modelos existentes:** `User`, `Plan`, `Sale`, `CashCount`, `Outflow`.

| Excel (hoja.col) | Entidad actual / nueva | Acción |
|---|---|---|
| MOV. CLIENTES.FECHA | `Sale.date` | ✅ ya existe |
| MOV. CLIENTES.KARDEX | `Sale.clientCode` / **nuevo `Customer.code`** | ✅ existe como texto; ⚠️ crear tabla Cliente maestra |
| MOV. CLIENTES.NOMBRE | `Sale.clientName` / `Customer.name` | ✅ existe; ⚠️ dedupe por KARDEX |
| MOV. CLIENTES.TIPO DE SERVICIO | `Sale.serviceType` | ✅ existe (internet/tv/combo) — normalizar "INTERNET + TV ANALOGA"→combo |
| MOV. CLIENTES.PAQUETE | `Plan` (code/label) | ⚠️ **❌ no mapeable 1:1**: paquetes sin tabla maestra; limpiar nomenclatura |
| MOV. CLIENTES.MONTO INICIAL | `Sale.total` | ✅ existe (server-side) |
| MOV. CLIENTES.TIPO DE SOLICITUD | **nuevo `Sale.requestType`** | ❌ campo nuevo (default NUEVO CONTRATO) |
| MOV. CLIENTES.MOTIVO CAMBIO | **nuevo `Sale.changeReason`** | ❌ campo nuevo |
| MOV. CLIENTES.PAQUETE CAMBIO / MONTO FINAL / DIFERENCIA | **nuevo `Sale.planFrom` / `Sale.totalFrom`** | ❌ campo nuevo (para CAMBIO DE PLAN) |
| MOV. CLIENTES.CAJERA | `Sale.createdBy` (FK User) | ⚠️ mapear nombre→usuario (limpiar duplicados YENIFER) |
| MOV. CLIENTES.COMENTARIOS | `Sale.notes` | ❌ campo nuevo |
| CALIDAD.* (encuestas) | **nuevo modelo `Survey`** | ❌ módulo nuevo (importación automatizada) |
| QUEJAS.* | **nuevo modelo `Complaint`** (1..3 por cliente) | ❌ módulo nuevo |
| CAMBIOS.* | **nuevo modelo `ServiceChange`** | ❌ módulo nuevo |
| Proyección | **nuevo modelo `Projection`** | ❌ módulo nuevo |
| LISTAS (barrios, motivos, cajeras, lugares) | `Customer.address`, `Customer.neighborhood` + tablas de catálogo | ❌ tablas de referencia nuevas |
| Hoja1 (calendario) | no aplica | descartar |
| Gráfico1/2 | Dashboard (reportes/gráficos) | ✅ se reemplaza por el Dashboard React |

**Gap Analysis (funcionalidades):**

| Funcionalidad del Excel | ¿Existe en app? | Prioridad | Solución |
|---|---|---|---|
| Registrar venta/movimiento | ✅ Sí (`/sales`) | — | Extender campos de cambio de plan y solicitud |
| Dashboard de ventas | ✅ Parcial | Alta | Agregar filtros por tipo de solicitud, cajera, periodo; KPI nuevos contratos vs retiros |
| Importar datos históricos del Excel | ❌ No | **Alta** | Script `import_excel` (entregado) |
| Encuestas de satisfacción (CALIDAD) | ❌ No | Media | Módulo Survey + importación |
| Quejas (1..3 con técnico y tiempo) | ❌ No | Alta | Módulo Complaint con estados y alertas de vencimiento |
| Cambios de servicio con impacto monetario | ❌ No | Media | Módulo ServiceChange |
| Proyección mensual | ❌ No | Baja | Módulo Projection |
| Exportar reporte (PDF/XLSX) | ✅ Sí | — | Ya cubierto |
| Notificaciones de pendientes | ❌ No | Media | Lista de pendientes por cajera/encargado |
| Lista maestra de clientes (KARDEX único) | ❌ No | **Alta** | Tabla `Customer` + dedupe |
| Catálogos (barrios, motivos, paquetes) | ❌ No | Media | Tablas de referencia + desplegables |

---

## 5. Plan de Migración

**Estrategia recomendada:** Migración **por fases** (Opción B). Los módulos que están vacíos en el Excel (QUEJAS, CAMBIOS, CALIDAD) se construyen primero como funcionalidad y se alimentan desde la app; solo **MOV. CLIENTES** tiene volumen histórico (3322 filas) que importar.

| Fase | Alcance | Duración est. |
|---|---|---|
| **F1** | Modelo: `Customer`, campos extra en `Sale`, catálogos (barrios, motivos, paquetes) + dedupe | 1 semana |
| **F2** | Script de importación de MOV. CLIENTES + validación de integridad | 2-3 días |
| **F3** | Módulos nuevos: Quejas, Cambios de servicio, Encuestas (formularios + listados) | 2 semanas |
| **F4** | Dashboard ampliado (tipos de solicitud, cajeras, proyección) + exportación | 1 semana |
| **F5** | Notificaciones/pendientes + capacitación y corte | 1 semana |

**Limpieza de datos previa (F1/F2):**
1. Normalizar cajeras (`YENNIFER`→`YENIFER`) y crear usuarios reales.
2. Corregir/descartar fechas corruptas (`10/04/205`) y montos negativos.
3. Unificar paquetes: `30 M`/`GO-60(FEB25)`/`GoBasic` → un solo catálogo `Plan`.
4. Crear `Customer` por KARDEX (3135 únicos) con el nombre más frecuente.
5. Validar integridad post-migración (counts, montos por cajera vs. Excel).

**Riesgos y mitigaciones:** pérdida de datos en limpieza (backup + `--dry-run`); rechazo del equipo por cambio de hábito (periodo en paralelo + capacitación); duplicados (dedupe por KARDEX + validación de unicidad en la app).

---

## 6. Entregables

| # | Entregable | Ubicación |
|---|---|---|
| 1 | Reporte de análisis (este documento) | `ANALISIS_MIGRACION.md` |
| 2 | Matriz de mapeo | sección 4 de este documento |
| 3 | Gap analysis priorizado | sección 4 |
| 4 | Plan de migración por fases | sección 5 |
| 5 | Script de importación | `core/management/commands/import_excel.py` |
| 6 | Mockups/UI de módulos nuevos | pendiente (cuando se aprueben los módulos de la F3) |

## 8. Estado de la migración (Fase 1+2 ejecutada)

**Modelo ampliado** (`core/models.py`, migración `core/0002_*`):
- Nuevo modelo `Customer` (maestro por KARDEX, clave única `code`).
- `Sale` ampliada: `requestType` (nuevo_contrato, cambio_plan, recontratacion, retiro, adicion, baja_temporal, otro), `changeReason`, `planFrom`, `totalFrom`, `notes` y FK `customer`.

**Importación ejecutada** (`python manage.py import_excel --file "ARCHIVO ATENCION AL CLIENTE 2026.xlsx"`):

| Métrica | Valor |
|---|---|
| Ventas importadas | 3,267 |
| Clientes (KARDEX únicos) | 3,117 |
| Planes creados desde el catálogo | 51 |
| Ingreso total | 678,107 Bs |
| Fechas | 2016-03-14 → 2026-08-05 |
| Filas omitidas | 54 (48 fecha inválida + 6 monto negativo) |

**Distribución importada:** `requestType` = nuevo_contrato 2,469 · cambio_plan 538 · retiro 179 · recontratacion 55 · adicion 25 · baja_temporal 1. `serviceType` = internet 2,218 · combo 583 · tv 466.

**Catálogo normalizado** (`python manage.py normalize_catalog`): solo planes vigentes.
- 22 planes legacy eliminados ("30 M", "25 M", "SERVICIO BASICO 1/2", "GOHFC", "FULLHD-HFC", "BASICO SD", "COMERCIAL", genéricos GEN, "NO APLICA", etc.) y sus ventas re-apuntadas al equivalente vigente (e.g. `30 M` → `GO-120(JUL24)`, `SERVICIO BASICO` → `TV-120`).
- Quedan **33 planes activos** con la lista de precios real (Bs/mes): GO-30(90) · GO-40(130) · GO-50(145) · GO-60(230) · GO-90(175) · GO-120(190) · GO-200(290) · GO-300(260) · GO-400(360) · GoBasic(230) · GoStandard(290) · GoPremium(360) · GOINT-30/50/80/140 (515/562/810/1487) · GOEMP-40(2260) · TV-120(170) · GOHD(180) · COMERCIAL(900) · GOTV-120/121-125(300) · GOTV-300(350) · GOTV-400(260) · GOTV-500(470) · GOTV-60(230) · GoDuoBasic(300) · GoDuoGamer(350).

**App adaptada a MOV. CLIENTES (anti-burocracia):**
- Formulario "Nuevo Movimiento": autocompletar cliente por kardex/nombre (crea el `Customer` automáticamente si no existe), desplegable de tipo de solicitud, motivo de cambio condicional (solo en cambios de plan), comentarios opcionales y total calculado desde el plan. Sin campos redundantes del Excel.
- **Selector de plan inteligente:** en el alta de un movimiento solo se ofrecen los **planes vigentes**; si el tipo de solicitud es `retiro`, también se pueden seleccionar los **planes anteriores** (catálogo legacy) agrupados en "Planes anteriores", para registrar a qué plan daba de baja el cliente.
- Listado con filtro por tipo de movimiento y badge del tipo.
- Endpoint `GET /api/customers?q=` para búsqueda de clientes.

**Normalización de datos (comandos):**
- `normalize_catalog`: plan `legacy` = superado por una versión nueva (ej. `GOTV-120` → `GOTV-120(FEB25)`); queda descartado del alta pero disponible para retiros. Catálogo: 33 activos (32 vigentes + 1 legacy).
- `normalize_customers`: fusiona clientes repetidos por nombre normalizado (una persona registrada con varios kardex, ej. `13316`/`20123-1`/`14511`). Canonico = el de más ventas y código limpio; re-apunta las ventas (`customer` FK y `clientCode`) y elimina los duplicados. Resultado: **203 clientes fusionados, 204 ventas re-apuntadas**, clientes de 3,117 → **2,914**, 0 duplicados, sin ventas huérfanas.

**API:** `SaleSerializer`/`SaleCreateSerializer` exponen y aceptan los campos nuevos; 19/19 tests OK.

**Producción (Wasmer):** el bootstrap de `wsgi.py` ahora corre `seed --users-only` (solo garantiza los usuarios, ya no inserta datos mock). Flujo para poblar datos reales en la nube: `import_excel` → `normalize_catalog`.

**Pendiente:** migrar la Fase 3 (módulos de quejas/cambios/encuestas) y refinar el Dashboard con KPI de MOV. CLIENTES (nuevos contratos vs retiros, por cajera y por mes).

---

## 7. Preguntas para validar contexto

1. ¿Los clientes (KARDEX) tienen datos maestros adicionales (barrio, teléfono, dirección) fuera del Excel? → afecta el modelo `Customer`.
2. ¿Quiénes deben poder ver/editar quejas y cambios de servicio? → roles y permisos.
3. ¿Qué reportes críticos se necesitan primero? (sugerido: nuevos contratos vs retiros por mes y por cajera).
4. ¿Se integra con SOFTV/TopSAP o el archivo seguirá siendo la fuente manual?
5. ¿Plazo objetivo para cortar el Excel y usar solo la app?
