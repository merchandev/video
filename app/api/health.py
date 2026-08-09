import os
import shutil
from fastapi import APIRouter
import httpx

router = APIRouter()

@router.get("/health")
async def health():
    comfyui_status = False
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get("http://comfyui:8188/system_stats", timeout=3.0)
            if res.status_code == 200:
                comfyui_status = True
    except:
        pass
        
    total, used, free = shutil.disk_usage("/app/data")
    
    return {
        "status": "ok",
        "docker": True,
        "comfyui": comfyui_status,
        "disk_free_gb": round(free / (2**30), 2)
    }
