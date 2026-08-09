Write-Host "=== Diagnóstico de Hardware (NVIDIA) ==="
$nvidia_smi = Get-Command "nvidia-smi" -ErrorAction SilentlyContinue

if ($nvidia_smi) {
    # Forma simplificada de obtener VRAM en Windows usando WMI o nvidia-smi
    $vramInfo = nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits
    $vramGB = [math]::Round([int]$vramInfo / 1024)
    Write-Host "GPU NVIDIA Detectada."
    Write-Host "VRAM Total Aproximada: $vramGB GB"
    
    if ($vramGB -le 6) {
        Write-Host "Recomendación: LOW VRAM EXTREME (No recomendado para Wan2.2 nativo, usa cuantización)" -ForegroundColor Red
    } elseif ($vramGB -le 8) {
        Write-Host "Recomendación: LOW VRAM (Compatible con Wan2.2 5B vía ComfyUI native offload)" -ForegroundColor Yellow
    } elseif ($vramGB -le 16) {
        Write-Host "Recomendación: BALANCED" -ForegroundColor Green
    } else {
        Write-Host "Recomendación: HIGH PERFORMANCE" -ForegroundColor Cyan
    }
} else {
    Write-Host "No se encontró nvidia-smi en el Host. Asegúrate de tener los drivers NVIDIA instalados." -ForegroundColor Yellow
}
