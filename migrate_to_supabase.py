#!/usr/bin/env python3
"""
Migracion SQLite -> PostgreSQL (Supabase)
Ejecutar desde la maquina local con PostgreSQL accesible.

Uso:
    1. Copia .env.example a .env y pon tu DATABASE_URL de Supabase
    2. Ejecuta: python migrate_to_supabase.py
"""
import os
import sys
import django

# Configurar Django con DATABASE_URL del .env
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salestracker.settings')

# Cargar .env si existe
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

if not os.environ.get('DATABASE_URL'):
    print('ERROR: DATABASE_URL no configurado.')
    print('Copia .env.example a .env y pon tu connection string de Supabase.')
    sys.exit(1)

django.setup()

from django.core.management import call_command

def main():
    print('=== Migracion SQLite -> PostgreSQL (Supabase) ===')
    print()

    # 1. Ejecutar migraciones de Django (crea las tablas)
    print('[1/3] Ejecutando migraciones de Django...')
    call_command('migrate', 'core', verbosity=1)
    call_command('migrate', 'auth', verbosity=1)
    call_command('migrate', 'contenttypes', verbosity=1)
    call_command('migrate', 'admin', verbosity=1)
    call_command('migrate', 'sessions', verbosity=1)
    print('      Migraciones completadas.')
    print()

    # 2. Cargar fixture de planes
    print('[2/3] Cargando planes desde fixture...')
    from core.models import Plan
    if not Plan.objects.exists():
        call_command('loaddata', 'planes', verbosity=1)
        print('      Planes cargados.')
    else:
        print('      Planes ya existen, saltando.')
    print()

    # 3. Crear usuarios
    print('[3/3] Creando usuarios...')
    call_command('seed', '--users-only', verbosity=1)
    print()

    # Verificar
    from core.models import User, Plan, Sale, Customer
    print('=== Verificacion ===')
    print(f'  Usuarios: {User.objects.count()}')
    print(f'  Planes:   {Plan.objects.count()}')
    print(f'  Ventas:   {Sale.objects.count()}')
    print(f'  Clientes: {Customer.objects.count()}')
    print()
    print('Migracion completada exitosamente!')

if __name__ == '__main__':
    main()
