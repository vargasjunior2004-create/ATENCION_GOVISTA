# Fase 0 — Estado inicial reproducible

Fecha de medición: 2026-10-29 UTC  
Rama: `fase-0/linea-base`  
Commit base: `02adeaa0649fe3bf7472bf9bb997e4d63af31261`

## Objetivo y alcance

Se midió el estado real del repositorio sin modificar comportamiento de la
aplicación. Esta fase solo agrega documentación y scripts de conveniencia.

## Reproducción

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py check
.venv/bin/python manage.py test
```

En Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py check
python manage.py test
```

Atajos disponibles:

```bash
./scripts/test.sh check
./scripts/test.sh test
./scripts/test.sh test-core
./scripts/test.sh lint
```

El lint queda como aviso hasta la Fase 8 porque todavía no hay herramienta ni
configuración de lint en el proyecto.

## Versiones instaladas

La instalación desde los rangos actuales produjo:

- Python 3.13.5
- Django 6.1.2
- Django REST Framework 3.18.3
- SimpleJWT 5.5.1
- ReportLab 5.1.0
- openpyxl 3.1.5
- Gunicorn 26.2.0
- psycopg2-binary 2.9.13

La lista completa está en `pip-freeze.txt`. Las dependencias no están fijadas;
esto queda para la Fase 8.

## Evidencia de pruebas

| Comando | Resultado |
|---|---|
| `.venv/bin/python manage.py check` | OK, sin issues |
| `.venv/bin/python manage.py test` | 157 tests OK, 2 skipped |
| Duración de la suite | 366.552 s |

Salidas completas:

- `check.txt`
- `tests.txt`
- `versiones.txt`
- `pip-freeze.txt`

Durante los tests se observó salida de consola con payloads completos de
ventas. No se corrigió en esta fase; queda asignado a Fase 3.

## Métricas

- Tamaño del árbol de trabajo: 1.1 GB
- Tamaño de `.git`: 104 MB
- `staticfiles/`: 95 MB, 503 archivos versionados
- `frontend_build/`: 4.3 MB, 7 archivos versionados
- Archivos versionados totales: 621
- Bundles JS/CSS en `staticfiles/`: 149
- Source maps en `staticfiles/` y `frontend_build/`: 41
- Fixture `core/fixtures/planes.json`: 33 planes
- Base SQLite local: 34 planes y 4 ventas
- Métodos de prueba descubiertos: 157
- Migración más reciente: `0027_trasladoexterno.py`

Los valores se reproducen en `metricas.txt`.

## Hallazgos y clasificación inicial

### Preexistentes confirmados

- Dependencias declaradas con rangos abiertos.
- `.env`, SQLite, `export_data.json`, PDF generado y artefactos de frontend
  presentes en el árbol de trabajo; varios también están versionados.
- `staticfiles/` versionado y con múltiples bundles/source maps.
- Configuración con valores de producción inseguros y fallback de base de datos;
  se verificará y corregirá en Fases 1 y 2.
- Payloads completos de ventas visibles durante las pruebas; Fase 3.
- Diferencia entre 33 planes del fixture y 34 de la base local.

### Dependientes del entorno

- La suite requiere una instalación de dependencias compatible. En este entorno
  limpio se instaló correctamente mediante `requirements.txt`.
- Las métricas de la base local no representan producción.

### Fallos

- No se registraron fallos de tests: 157 OK y 2 omitidos.
- El primer intento fue interrumpido por un límite externo de 120 segundos; se
  repitió con 600 segundos y finalizó correctamente en 366.552 s.

## Variables mínimas documentadas para el entorno futuro

La aplicación usa o debe formalizar estas variables en las Fases 1 y 2:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DATABASE_URL`
- `BACKUP_DATABASE_URL`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`

No se incluyen valores en esta documentación.

## Riesgos y rollback

Riesgo bajo: esta fase agrega solo documentación, scripts y el entorno local
`.venv/`. Rollback: revertir el PR de `fase-0/linea-base`.

## Pendientes de esta fase

- La purga de secretos/datos y la limpieza de artefactos no se ejecutan aquí;
  requieren Fases 1 y 9, con coordinación y evidencia específica.
- No se ejecutó ninguna migración contra producción.
