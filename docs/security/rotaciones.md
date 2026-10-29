# Registro de rotaciones y cuentas — Fase 1

## Estado

Este documento registra el procedimiento pendiente sin almacenar secretos ni
contraseñas. La aplicación local ya no contiene una clave en `app.yaml` ni
`export_data.json` en el árbol de trabajo.

## Acciones obligatorias antes de producción

1. Generar una nueva `DJANGO_SECRET_KEY` con un generador seguro.
2. Cargarla en el gestor de secretos del proveedor activo, nunca en Git.
3. Invalidar sesiones y tokens JWT emitidos con la clave anterior.
4. Revisar los logs del proveedor desde el primer commit que expuso la clave.
5. Cambiar las credenciales de las cuentas administrativas que hayan usado
   contraseñas por defecto o estén presentes en exportaciones.
6. Reescribir el historial para eliminar `export_data.json` y cualquier secreto
   expuesto, coordinando todos los clones y haciendo force-push controlado.
7. Verificar con `git log --all -- export_data.json` y un escáner de secretos.

## Bloqueos actuales

- No hay acceso al panel del proveedor desde este entorno; la rotación no se
  ejecutó ni se simuló.
- `export_data.json` fue eliminado de esta rama, pero todavía aparece en el
  historial anterior (`8df312e`) hasta ejecutar una purga coordinada.
- No se puede declarar P0 cerrado mientras la purga y la rotación no tengan
  evidencia del proveedor.

## Seed seguro

El comando `seed` ya no contiene contraseñas fijas. Requiere estas variables
temporales, proporcionadas por el gestor de secretos o por la sesión local:

```text
DJANGO_SEED_ADMIN_NAME
DJANGO_SEED_ADMIN_PASSWORD
DJANGO_SEED_SALES_NAME
DJANGO_SEED_SALES_PASSWORD
```

En producción rechaza contraseñas cortas o conocidas. Las variables deben
eliminarse de la sesión después de ejecutar el comando.

## Rollback

La eliminación de archivos sensibles del árbol se revierte solo mediante el
commit anterior después de confirmar que ningún despliegue volverá a leerlos.
La rotación de una clave no tiene rollback seguro: si falla, se corrige hacia
adelante con otra clave y se invalidan las sesiones nuevamente.
