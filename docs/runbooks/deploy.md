# Runbook de despliegue — Fase 2

## Principios

- El build solo instala dependencias y genera archivos estáticos.
- El arranque WSGI/ASGI no ejecuta migraciones ni seed.
- Las migraciones se ejecutan una sola vez desde el release command.
- Producción requiere `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`,
  `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS` y
  `DJANGO_CSRF_TRUSTED_ORIGINS`.

## Release en Render

Configurar el release command del servicio como:

```bash
bash scripts/release.sh
```

El script toma un advisory lock de PostgreSQL antes de ejecutar `migrate`.
Después, el servicio web puede arrancar con:

```bash
gunicorn salestracker.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 60
```

## Health checks

- `/api/health`: liveness, no consulta la base y devuelve solo `status`.
- `/api/ready`: comprueba conexión y migraciones pendientes; devuelve `503`
  sin detalles de infraestructura cuando no está listo.

## Rollback

1. Detener el deploy nuevo en Render.
2. Volver al commit anterior desde el historial del servicio.
3. No revertir migraciones automáticamente.
4. Si una migración es incompatible, restaurar la base desde el backup y
   coordinar una migración correctiva.

No ejecutar `migrate` desde una máquina local contra producción.

## Limitación conocida

El refresh token rota, pero no se habilita todavía el blacklist de SimpleJWT:
el proyecto usa `core.User` en lugar del usuario Django estándar y la app de
blacklist no puede relacionar ambos modelos. La revocación persistente de
tokens queda registrada para una fase específica de autenticación; no se
simula con una configuración incompatible.
