# Backlog de auditoría

Este backlog reúne riesgos detectados que no se implementan durante la Fase 0.
Cada ítem debe resolverse en la fase indicada y en una rama/PR separado.

## P0

- **Fase 1 — Secretos y datos expuestos:** rotar la clave expuesta, purgar
  `export_data.json` del historial, eliminar credenciales por defecto, añadir
  escaneo de secretos y completar `.gitignore`.
- **Fase 2 — Configuración y despliegue:** eliminar fallbacks inseguros,
  endurecer settings, separar health/readiness y sacar migraciones del arranque.
- **Fase 3 — Reportes y privacidad:** corregir firma y expiración de enlaces,
  minimizar PII, eliminar payloads sensibles de logs y aplicar throttling.
- **Fase 4 — Respaldos:** automatizar, cifrar, verificar y probar restauración.

## P1

- **Fase 5 — Integridad:** corregir el cálculo de edición de traslados,
  borrados protegidos, auditoría, soft delete, idempotencia y locking.
- **Fase 6 — API:** limitar paginación/rangos, uniformar errores y publicar
  OpenAPI.
- **Fase 7 — Reportes:** imponer límites y mover reportes grandes a trabajos
  asíncronos.
- **Fase 8 — Calidad:** fijar dependencias, CI, lint, cobertura y escaneo de
  vulnerabilidades.
- **Fase 9 — Repositorio:** dejar de versionar `staticfiles/`, `frontend_build/`
  y artefactos generados; completar metadatos del proyecto.

## P2

- **Fase 10:** extraer servicios, selectores y una única fuente de precios.
- **Fase 11:** refresh JWT, inactividad real y manejo centralizado de errores en
  frontend.
- **Fase 12:** logging estructurado, request ID, métricas, Sentry y alertas.
- **Fase 13:** actualizar README, arquitectura, ADRs, runbooks y documentación
  de traslados.
- **Fase 14:** regresión, carga, restore, evidencias y release final.

## Discrepancias confirmadas en la línea base

- `requirements.txt` y `pyproject.toml` usan rangos; no existe una versión
  reproducible declarada. La instalación de referencia obtuvo Django 6.1.2.
- El fixture contiene 33 planes, mientras la base SQLite local tiene 34.
- La base SQLite local tiene 4 ventas; cualquier cifra histórica de producción
  debe verificarse contra una copia autorizada, no contra este entorno.
- El repositorio contiene artefactos y datos sensibles detectados por la línea
  base; su eliminación corresponde a Fases 1 y 9, no a esta fase.
