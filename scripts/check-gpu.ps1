Write-Host "=== Diagnóstico de Hardware (NVIDIA) para SkyReels ==="
$nvidia_smi = Get-Command "nvidia-smi" -ErrorAction SilentlyContinue

if ($nvidia_smi) {
    $vramInfo = nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits
    $vramGB = [math]::Round([int]$vramInfo / 1024)
    Write-Host "GPU NVIDIA Detectada."
    Write-Host "VRAM Total Aproximada: $vramGB GB"
    
    if ($vramGB -le 6) {
        Write-Host "Perfil Automático: EXTREME LOW VRAM" -ForegroundColor Red
        Write-Host "Se forzará enable_sequential_cpu_offload() y resoluciones mínimas. El número de frames base se bajará a 57 para prevenir OOM."
    } elseif ($vramGB -le 8) {
        Write-Host "Perfil Automático: LOW VRAM (RTX 3050 class)" -ForegroundColor Yellow
        Write-Host "Se activará enable_sequential_cpu_offload(). El número de frames base se bajará a 77 para máxima estabilidad."
    } elseif ($vramGB -le 16) {
        Write-Host "Perfil Automático: BALANCED" -ForegroundColor Green
        Write-Host "Se activará enable_sequential_cpu_offload() para permitir resoluciones mayores."
    } else {
        Write-Host "Perfil Automático: NATIVE" -ForegroundColor Cyan
        Write-Host "Inferencia nativa rápida en VRAM a 97 frames."
    }
} else {
    Write-Host "No se encontró nvidia-smi en el Host. Asegúrate de tener los drivers NVIDIA instalados." -ForegroundColor Yellow
}
