# Ubicación de Clientes: almacenamiento privado

El módulo guarda únicamente la ruta del objeto en PostgreSQL. La fotografía se
sube desde Django a un bucket privado de Supabase Storage y las respuestas API
devuelven URLs firmadas con expiración corta.

## Configuración requerida

Definir en Render (Environment), nunca en el repositorio:

```text
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<clave privada del servidor>
SUPABASE_STORAGE_BUCKET=ubicaciones-clientes
```

Crear previamente el bucket privado `ubicaciones-clientes`. La clave
`SUPABASE_SERVICE_ROLE_KEY` solo debe existir en el backend; no se entrega al
frontend ni se incluye en URLs.

La aplicación acepta JPG/JPEG, PNG y WebP, los normaliza a JPEG y limita el
resultado a 5 MB. HEIC no se acepta todavía porque el entorno no incluye un
decodificador HEIC confiable; el teléfono puede entregar JPEG seleccionando la
opción de compatibilidad de cámara.
