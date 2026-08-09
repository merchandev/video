import json
import httpx
import os
import asyncio
from app.db.models import Job
from pathlib import Path

COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://comfyui:8188")
WORKFLOWS_DIR = Path("/app/comfyui/workflows")

async def run_comfy_workflow(job: Job):
    wf_name = "wan22_i2v.json" if job.image_path else "wan22_t2v.json"
    wf_path = WORKFLOWS_DIR / wf_name
    
    try:
        if not wf_path.exists():
            return False, "Workflow de ComfyUI no encontrado"
            
        with open(wf_path, "r") as f:
            workflow = json.load(f)
            
        # NOTA: La inyección de datos reales al JSON depende de la estructura de nodos.
        # En ComfyUI, los nodos tienen un ID numérico (ej. "3").
        # Aquí se actualizaría de forma segura (sin ejecutar python dinámico).
        
        async with httpx.AsyncClient() as client:
            payload = {"prompt": workflow}
            res = await client.post(f"{COMFYUI_URL}/prompt", json=payload, timeout=10.0)
            
            if res.status_code != 200:
                return False, f"Error en ComfyUI API: {res.text}"
                
            data = res.json()
            prompt_id = data.get("prompt_id")
            
            # Polling básico de finalización
            while True:
                hist_res = await client.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10.0)
                hist_data = hist_res.json()
                if prompt_id in hist_data:
                    break
                await asyncio.sleep(3)
                
            # POST-PROCESO FFMPEG
            # En la V2 real, ComfyUI genera el video en /data/outputs/temp_...mp4
            # Aquí invocaríamos a ffmpeg (usando asyncio.create_subprocess_exec)
            # para recortar y forzar a la resolución final requerida.
            
            return True, None
            
    except Exception as e:
        return False, str(e)
