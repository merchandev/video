#!/bin/bash
set -euo pipefail
echo "=== Instalación de Local Video Studio (SkyReels V2) ==="

echo -e "\n1. Comprobando Docker..."
if ! command -v docker &> /dev/null
then
    echo "Docker no está instalado. Instálalo primero."
    exit 1
fi

echo -e "\n2. Comprobando acceso a GPU desde Docker..."
if ! docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi &> /dev/null
then
    echo "No se pudo acceder a la GPU NVIDIA en Docker. Asegúrate de tener el NVIDIA Container Toolkit instalado."
    exit 1
fi

echo -e "\n3. Construyendo imagen V3 (Diffusers Native)..."
docker compose build

echo -e "\n3. Descargando pesos de SkyReels V2 (I2V y DF)..."
docker compose --profile tools run --rm model-downloader

echo -e "\n4. Iniciando Local Video Studio..."
docker compose up -d

echo -e "\n=== Todo listo ==="
echo "Abre http://localhost:7860 en tu navegador."
