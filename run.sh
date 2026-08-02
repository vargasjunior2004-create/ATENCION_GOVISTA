#!/bin/bash
set -e

echo "=== SaleStracker ==="

# Instalar dependencias del backend (Django)
echo "Instalando dependencias del backend..."
pip3 install --break-system-packages -r requirements.txt

# Instalar dependencias del frontend
echo "Instalando dependencias del frontend..."
cd frontend
npm install

# Crear directorio de datos
mkdir -p ../data

# Compilar frontend para producción
echo "Compilando frontend..."
npm run build
rm -rf ../frontend_build
cp -r build ../frontend_build

# Migraciones + seed de datos mock
echo "Preparando base de datos..."
cd ..
python3 manage.py migrate
python3 manage.py seed

# Iniciar backend Django en modo producción
echo "Iniciando backend en http://localhost:4000 ..."
python3 manage.py runserver 0.0.0.0:4000
