# Backup manual cifrado — Fase 4

Esta solución no usa almacenamiento de Render. El archivo cifrado debe
guardarse fuera del repositorio, por ejemplo en un disco externo cifrado o en
un almacenamiento privado administrado por el responsable.

## Variables temporales

```bash
export DATABASE_URL='URL de la aplicación'
export BACKUP_DATABASE_URL='URL Session Pooler de Supabase'
export BACKUP_ENCRYPTION_PASSPHRASE='passphrase larga guardada fuera del proyecto'
export BACKUP_OUTPUT_DIR="$HOME/govista-backups"
```

La passphrase no debe escribirse en `.env`, Git, tickets ni chats.

## Generar backup

Desde la raíz del proyecto:

```bash
./scripts/backup_encrypted.py
```

El resultado contiene:

- `*.dump.enc`: dump cifrado.
- `*.dump.enc.sha256`: checksum del archivo cifrado.

El dump sin cifrar se elimina automáticamente. Verifica el checksum:

```bash
sha256sum -c govista-backups/*.sha256
```

## Restauración en una base de staging/local

Nunca restaures directamente sobre producción. Descifra en una carpeta
temporal protegida:

```bash
umask 077
openssl enc -d -aes-256-cbc -pbkdf2 \
  -in govista-backups/ARCHIVO.dump.enc \
  -out /tmp/govista-restore.dump \
  -pass env:BACKUP_ENCRYPTION_PASSPHRASE
pg_restore --clean --if-exists --no-owner --no-privileges \
  --dbname "$RESTORE_DATABASE_URL" /tmp/govista-restore.dump
rm -f /tmp/govista-restore.dump
```

Después ejecuta `manage.py check`, `migrate --plan` y compara conteos de
`core_sale`, `core_customer`, `core_user` y `core_trasladoexterno`.

## RPO/RTO y limitación

Con este procedimiento el RPO depende de la frecuencia manual. Objetivo
provisional: backup diario, RPO ≤ 24 horas. El RTO debe medirse en cada
simulacro de restauración. La automatización y el almacenamiento remoto quedan
pendientes de disponer de un job y almacenamiento adecuados.

## Decisión temporal del MVP

Durante el MVP no se contratará un job ni almacenamiento adicional. El dueño
del sistema acepta temporalmente el riesgo de un RPO manual y ejecutará el
backup cifrado antes de migraciones, cambios de configuración sensibles o
despliegues de alto riesgo. Esta decisión debe revisarse si el proyecto pasa a
operación productiva crítica o recibe inversión para Supabase.
