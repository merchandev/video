Write-Host "=== Iniciando Local Video Studio (SkyReels V2) ==="
docker compose up -d
Write-Host "Abriendo http://localhost:7860 en tu navegador..."
Start-Process "http://localhost:7860"
