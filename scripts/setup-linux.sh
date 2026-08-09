#!/bin/bash
set -e

echo "=== Instalación de LocalWan Studio ==="

echo -e "\n1. Comprobando Docker..."
if ! command -v docker &> /dev/null; then
    echo "Error: Docker no está instalado."
    exit 1
fi

echo -e "\n2. Comprobando acceso a GPU desde Docker..."
if ! docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi; then
    echo "Error: No se pudo acceder a la GPU NVIDIA en Docker."
    exit 1
fi

echo -e "\n3. Construyendo imagen..."
docker compose build wan-studio

echo -e "\n4. Descargando modelo Wan2.2-TI2V-5B..."
docker compose --profile tools run --rm model-downloader

echo -e "\n5. Iniciando aplicación..."
docker compose up -d wan-studio

echo -e "\n=== Todo listo ==="
echo "Abre tu navegador en http://localhost:7860"
