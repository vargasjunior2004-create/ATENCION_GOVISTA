#!/bin/bash
set -e

echo "=== SaleStracker ==="

# Instalar dependencias del backend
echo "Instalando dependencias del backend..."
cd backend && npm install

# Instalar dependencias del frontend
echo "Instalando dependencias del frontend..."
cd ../frontend && npm install

# Crear directorio de datos
mkdir -p ../backend/data

# Compilar frontend para producción
echo "Compilando frontend..."
npm run build

# Iniciar backend en modo producción
echo "Iniciando backend..."
cd ../backend
NODE_ENV=production node src/index.js
