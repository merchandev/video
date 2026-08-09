Write-Host "=== Instalación de LocalWan Studio ==="

Write-Host "`n1. Diagnóstico de Sistema..."
.\scripts\check-gpu.ps1

Write-Host "`n2. Comprobando Docker..."
docker --version
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker no está instalado o no se encuentra en el PATH. Instala Docker Desktop y activa WSL2."
    exit 1
}

Write-Host "`n3. Comprobando acceso a GPU desde Docker..."
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
if ($LASTEXITCODE -ne 0) {
    Write-Error "No se pudo acceder a la GPU NVIDIA en Docker."
    exit 1
}

Write-Host "`n4. Construyendo imágenes V2 (FastAPI y ComfyUI)..."
docker compose build

Write-Host "`n5. Descargando pesos de Wan2.2-TI2V-5B..."
docker compose --profile tools run --rm model-downloader

Write-Host "`n6. Iniciando LocalWan Studio V2..."
docker compose up -d

Write-Host "`n=== Todo listo ==="
Write-Host "Abriendo http://localhost:7860 en tu navegador..."
Start-Sleep -Seconds 3
Start-Process "http://localhost:7860"
