from fastapi import APIRouter
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import os

router = APIRouter()
OUTPUTS_DIR = Path("/app/data/outputs")

@router.get("/files/outputs/{filename}")
async def get_output_file(filename: str):
    # Sanitize
    clean_name = os.path.basename(filename)
    file_path = OUTPUTS_DIR / clean_name
    
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    return JSONResponse(status_code=404, content={"error": "File not found"})
