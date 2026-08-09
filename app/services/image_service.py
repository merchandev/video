from PIL import Image, ImageOps
from pathlib import Path
from fastapi import UploadFile, HTTPException

INPUTS_DIR = Path("/app/data/inputs")

async def save_and_verify_image(job_id: str, file: UploadFile) -> str:
    try:
        content = await file.read()
        
        # Guardar temporal
        temp_path = INPUTS_DIR / f"temp_{job_id}"
        with open(temp_path, "wb") as f:
            f.write(content)
            
        # Verificar y convertir con Pillow
        with Image.open(temp_path) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode != "RGB":
                img = img.convert("RGB")
                
            img.thumbnail((2048, 2048))
            
            final_name = f"{job_id}.png"
            final_path = INPUTS_DIR / final_name
            img.save(final_path, format="PNG")
            
        temp_path.unlink()
        return str(final_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail="El archivo subido no es una imagen válida.")
