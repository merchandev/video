Write-Host "=== Instalación de LocalWan Studio ==="

Write-Host "`n1. Comprobando Docker..."
docker --version
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker no está instalado o no se encuentra en el PATH. Instala Docker Desktop y activa WSL2."
    exit 1
}

Write-Host "`n2. Comprobando acceso a GPU desde Docker..."
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
if ($LASTEXITCODE -ne 0) {
    Write-Error "No se pudo acceder a la GPU NVIDIA en Docker. Asegúrate de tener los drivers instalados y la integración con WSL2 activada en Docker Desktop."
    exit 1
}

Write-Host "`n3. Construyendo imagen..."
docker compose build wan-studio

Write-Host "`n4. Descargando modelo Wan2.2-TI2V-5B (Esto puede tardar según tu conexión)..."
docker compose --profile tools run --rm model-downloader

Write-Host "`n5. Iniciando aplicación..."
docker compose up -d wan-studio

Write-Host "`n=== Todo listo ==="
Write-Host "Abriendo http://localhost:7860 en tu navegador..."
Start-Sleep -Seconds 3
Start-Process "http://localhost:7860"
