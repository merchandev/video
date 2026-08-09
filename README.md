# Local Video Studio

Generador de video local basado enteramente en la integración oficial de **SkyReels-V2** mediante HuggingFace `diffusers`.

- **Imagen → Video** (I2V)
- **Texto → Video** (Diffusion Forcing)
- **Primer frame → último frame**
- **Extensión de Video**
- Interfaz web local consolidada
- Offload de CPU Secuencial para compatibilidad con **Low VRAM (ej. RTX 3050 8GB)**
- 24 fps
- Cola de generación robusta sobre SQLite (1 trabajo en GPU a la vez)
- Sin cuentas, créditos ni API de pago

## Requisitos recomendados (Windows)

- Windows 10/11 actualizado
- Docker Desktop usando backend WSL2
- Espacio en disco: mínimo 65GB libres (I2V ocupa ~32GB, DF ~29GB)
- GPU NVIDIA: 8GB experimental con sequential CPU offload y perfil Extreme. 16GB+ recomendado para una experiencia más cómoda.
- Driver NVIDIA actualizado

## Instalación Automática (Windows)

Abre PowerShell en esta carpeta y ejecuta:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-windows.ps1
```

Este script:
1. Validará tu GPU y aplicará perfiles.
2. Construirá la imagen Docker localmente, instalando PyTorch y `diffusers`.
3. Descargará ambos modelos de Skywork (I2V y DF).
4. Levantará la API FastAPI en `http://localhost:7860`.

## Iniciar el servidor

Para arrancar el servidor en usos posteriores, utiliza:

```powershell
.\scripts\start.ps1
```

## Arquitectura V3
- **FastAPI**: Maneja todo el servidor en un solo proceso `app/main.py`.
- **Inferencia**: Utiliza los Pipelines nativos `SkyReelsV2ImageToVideoPipeline` y `SkyReelsV2DiffusionForcingPipeline` gestionados en `app/model_manager.py`.
- **Offloading**: Para GPUs de menos de 16GB, el sistema aplica automáticamente `enable_sequential_cpu_offload()` para garantizar que el modelo entre en la VRAM disponible, reduciendo si es necesario los `base_num_frames` a 77 o 57.
- **FFmpeg**: Todo resultado RAW se interpola y recorta exactamente al formato deseado (1280x720 o 720x1280) localmente por CPU para no comprometer memoria GPU.
