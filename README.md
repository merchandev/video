# LocalWan Studio (V2)

Generador de video local avanzado basado en **Wan2.2-TI2V-5B** orquestado por **FastAPI** y **ComfyUI**.

## Arquitectura

El sistema utiliza contenedores independientes (Docker Compose):
1. **API (FastAPI)**: Maneja peticiones web, procesa las imágenes y gestiona los trabajos en SQLite. No usa la GPU directamente.
2. **Motor (ComfyUI)**: Recibe los flujos JSON mediante API y encola los trabajos en la GPU. Soporta *offloading* nativo, permitiendo ejecutar Wan2.2 en tarjetas con menor VRAM (ej. 8 GB).

## Requisitos

- Windows 10/11 con WSL2.
- Driver NVIDIA actualizado.
- Docker Desktop con integración WSL2 activada.
- Tarjeta gráfica NVIDIA (Recomendado: 8 GB+ VRAM para Wan2.2 nativo).

## Instalación rápida en Windows

Abre PowerShell en esta carpeta y ejecuta:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-windows.ps1
```

Este script detecta tu GPU, construye los contenedores, descarga los modelos, e inicia la interfaz en `http://localhost:7860`.

## Uso

1. Entra a `http://localhost:7860`.
2. Sube una imagen de referencia (I2V) o ingresa un prompt (T2V).
3. Monitorea el proceso y descarga tu MP4 a la resolución exacta configurada.

## Ubicación de Datos

- `models/`: Pesos del modelo y checkpints de ComfyUI.
- `data/inputs/`: Imágenes de usuario preprocesadas.
- `data/outputs/`: Videos finales.
- `data/db/`: Base de datos SQLite (`jobs.db`).

## Licencias

El código de esta aplicación está licenciado bajo MIT. El modelo Wan2.2 está sujeto a su propia licencia oficial de uso (revisar repositorio de Wan-AI). ComfyUI se rige por su propia licencia GPL.
