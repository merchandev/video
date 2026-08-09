import os
import uuid
from typing import Optional
from pathlib import Path
from PIL import Image, ExifTags
from fastapi import FastAPI, BackgroundTasks, Depends, File, Form, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
import torch
import psutil

from app.db.database import engine, Base, get_db
from app.db.models import Job
from app.inference_worker import queue_job

# Inicializar BD
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Local Video Studio (SkyReels)")

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
INPUTS_DIR = DATA_DIR / "inputs"
OUTPUTS_DIR = DATA_DIR / "outputs"
INPUTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Limpiar trabajos atascados por reinicio del contenedor
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    stuck_jobs = db.query(Job).filter(Job.status.in_(["processing", "queued"])).all()
    for job in stuck_jobs:
        job.status = "failed"
        job.error = "Server restarted / Worker killed"
    db.commit()
    db.close()

# CORS no es necesario ya que se sirve todo desde el mismo origen

async def process_image(file_obj: UploadFile, prefix: str) -> str:
    try:
        img = Image.open(file_obj.file)
        
        # Corrección de orientación EXIF
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = dict(img._getexif().items())
            if exif[orientation] == 3:
                img = img.rotate(180, expand=True)
            elif exif[orientation] == 6:
                img = img.rotate(270, expand=True)
            elif exif[orientation] == 8:
                img = img.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            pass

        img = img.convert("RGB")
        path = str(INPUTS_DIR / f"{prefix}.png")
        img.save(path, format="PNG")
        return path
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Imagen inválida: {str(e)}")

def validate_model_integrity(model_path: Path, model_type: str) -> bool:
    import json
    required = [
        "model_index.json",
        "transformer/config.json",
        "vae/diffusion_pytorch_model.safetensors",
        "tokenizer/special_tokens_map.json",
        "tokenizer/spiece.model",
        "tokenizer/tokenizer.json",
        "tokenizer/tokenizer_config.json",
        "scheduler/scheduler_config.json",
        "text_encoder/config.json",
    ]
    if model_type == "i2v":
        required.extend([
            "image_encoder/config.json",
            "image_encoder/model.safetensors",
            "image_processor/preprocessor_config.json"
        ])
    
    for req in required:
        if not (model_path / req).exists():
            return False
            
    indexes = [
        "transformer/diffusion_pytorch_model.safetensors.index.json",
        "text_encoder/model.safetensors.index.json"
    ]
    
    for idx_file in indexes:
        idx_path = model_path / idx_file
        if idx_path.exists():
            try:
                with open(idx_path, "r", encoding="utf-8") as f:
                    idx_data = json.load(f)
                shards = set(idx_data.get("weight_map", {}).values())
                for shard in shards:
                    if not (idx_path.parent / shard).exists():
                        return False
            except Exception:
                return False
        else:
            # If index is missing, verify the un-sharded file exists
            unsharded_name = "diffusion_pytorch_model.safetensors" if "transformer" in idx_file else "model.safetensors"
            if not (idx_path.parent / unsharded_name).exists():
                return False

    return True

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/readiness")
def readiness_check():
    health_data = {
        "status": "ok",
        "gpu": False,
        "vram_gb": 0,
        "ram_gb": round(psutil.virtual_memory().total / (1024**3), 2)
    }
    
    if torch.cuda.is_available():
        health_data["gpu"] = True
        health_data["vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
        health_data["gpu_name"] = torch.cuda.get_device_name(0)
        
    base_model_dir = Path(os.environ.get("MODEL_DIR_BASE", "/models"))
    i2v_path = Path(os.environ.get("SKYREELS_I2V_MODEL_ID", base_model_dir / "SkyReels-V2-I2V-1.3B-540P-Diffusers"))
    df_path = Path(os.environ.get("SKYREELS_DF_MODEL_ID", base_model_dir / "SkyReels-V2-DF-1.3B-540P-Diffusers"))
    
    health_data["models"] = {
        "i2v": {
            "exists": i2v_path.exists(),
            "ready": validate_model_integrity(i2v_path, "i2v") if i2v_path.exists() else False
        },
        "df": {
            "exists": df_path.exists(),
            "ready": validate_model_integrity(df_path, "df") if df_path.exists() else False
        }
    }
    return health_data

@app.post("/api/generate")
async def generate_video(
    background_tasks: BackgroundTasks,
    mode: str = Form("i2v"),
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    image: Optional[UploadFile] = File(None),
    end_image: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    profile: str = Form("extreme"),
    orientation: str = Form("horizontal"),
    duration_seconds: int = Form(4),
    seed: int = Form(-1),
    ar_step: int = Form(0),
    overlap_history: int = Form(17),
    addnoise_condition: int = Form(20),
    db: Session = Depends(get_db)
):
    base_model_dir = Path(os.environ.get("MODEL_DIR_BASE", "/models"))
    
    valid_modes = ["i2v", "t2v", "first_last", "extend"]
    if mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Modo inválido: {mode}")

    valid_profiles = ["extreme", "low", "native"]
    if profile not in valid_profiles:
        raise HTTPException(status_code=400, detail=f"Perfil inválido: {profile}")
        
    valid_orientations = ["horizontal", "vertical"]
    if orientation not in valid_orientations:
        raise HTTPException(status_code=400, detail=f"Orientación inválida: {orientation}")

    if not 1 <= duration_seconds <= 15:
        raise HTTPException(status_code=400, detail="La duración debe estar entre 1 y 15 segundos.")
    if ar_step < 0:
        raise HTTPException(status_code=400, detail="ar_step debe ser >= 0")
    if overlap_history < 0:
        raise HTTPException(status_code=400, detail="overlap_history debe ser >= 0")
    if addnoise_condition < 0:
        raise HTTPException(status_code=400, detail="addnoise_condition debe ser >= 0")

    base_model_dir = Path(os.environ.get("MODEL_DIR_BASE", "/models"))
    i2v_path = Path(os.environ.get("SKYREELS_I2V_MODEL_ID", base_model_dir / "SkyReels-V2-I2V-1.3B-540P-Diffusers"))
    df_path = Path(os.environ.get("SKYREELS_DF_MODEL_ID", base_model_dir / "SkyReels-V2-DF-1.3B-540P-Diffusers"))
    
    if mode == "i2v" and duration_seconds <= 4:
        model_path = i2v_path
        model_type = "i2v"
    else:
        model_path = df_path
        model_type = "df"
        
    if not validate_model_integrity(model_path, model_type):
        raise HTTPException(
            status_code=400, 
            detail=f"MODELO INCOMPLETO para modo {mode}."
        )

    # Validar imágenes e inputs antes de continuar
    if mode in ["i2v", "first_last"] and not image:
        raise HTTPException(status_code=400, detail="Se requiere una 'image' para el modo seleccionado.")
    
    if mode == "first_last" and not end_image:
        raise HTTPException(status_code=400, detail="Se requiere un 'end_image' para el modo first_last.")
        
    if mode == "extend" and not video:
        raise HTTPException(status_code=400, detail="Se requiere un 'video' para el modo extend.")

    job_id = str(uuid.uuid4())
    image_path = None
    end_image_path = None
    video_path = None
    
    if mode in ["i2v", "first_last"] and image:
        image_path = await process_image(image, f"{job_id}_start")
    
    if mode == "first_last" and end_image:
        end_image_path = await process_image(end_image, f"{job_id}_end")
        
    if mode == "extend" and video:
        if video.size and video.size > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="El video excede el límite de 50MB.")
        video_path = str(INPUTS_DIR / f"{job_id}_ext.mp4")
        import shutil
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)
            
    # Base frames según perfil (reducción para VRAM)
    if profile == "extreme":
        width, height = (640, 368) if orientation == "horizontal" else (368, 640)
    elif profile == "low":
        width, height = (768, 432) if orientation == "horizontal" else (432, 768)
    else: # native
        width, height = (960, 544) if orientation == "horizontal" else (544, 960)
        
    # SkyReels: cálculo de frames
    if mode == "i2v" and duration_seconds <= 4:
        num_frames = duration_seconds * 24 + 1
    else:
        num_frames = ((duration_seconds * 24 - 1) // 4) * 4 + 1
        
        if ar_step > 0:
            causal_block_size = 5
            latent_frames = (num_frames - 1) // 4 + 1
            if latent_frames % causal_block_size != 0:
                # Auto-corregir num_frames
                latent_frames = ((latent_frames + causal_block_size - 1) // causal_block_size) * causal_block_size
                num_frames = (latent_frames - 1) * 4 + 1
        
    new_job = Job(
        id=job_id,
        mode=mode,
        prompt=prompt,
        negative_prompt=negative_prompt,
        image_path=image_path,
        end_image_path=end_image_path,
        video_path=video_path,
        seed=seed,
        profile=profile,
        width=width,
        height=height,
        frames=num_frames,
        ar_step=ar_step,
        overlap_history=overlap_history,
        addnoise_condition=addnoise_condition,
        status="queued",
        total_steps=30
    )
    db.add(new_job)
    db.commit()
    
    background_tasks.add_task(queue_job, job_id)
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
        
    progress = 0.0
    if job.status == "processing":
        if job.total_steps > 0:
            progress = min(0.99, job.current_step / job.total_steps)
    elif job.status == "completed":
        progress = 1.0
        
    return {
        "id": job.id,
        "status": job.status,
        "progress": progress,
        "error": job.error,
        "video_url": f"/api/jobs/{job_id}/video" if job.status == "completed" else None,
        "params": {
            "prompt": job.prompt,
            "negative_prompt": job.negative_prompt,
            "seed": job.seed,
            "mode": job.mode,
            "profile": job.profile,
            "width": job.width,
            "height": job.height,
            "frames": job.frames,
            "orientation": "horizontal" if job.width > job.height else "vertical",
            "ar_step": job.ar_step,
            "overlap_history": job.overlap_history,
            "addnoise_condition": job.addnoise_condition,
            "guidance_scale": 6.0 if job.mode == "t2v" else 5.0,
            "num_inference_steps": 30
        },
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None
    }

@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
        
    if job.status in ["completed", "failed"]:
        raise HTTPException(status_code=409, detail=f"Cannot cancel a job in state: {job.status}")
        
    if job.status in ["queued", "processing"]:
        job.status = "cancelled"
        db.commit()
        
    return {"status": "cancelled"}

@app.get("/api/jobs/{job_id}/video")
async def get_job_video(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job or job.status != "completed":
        raise HTTPException(status_code=404, detail="Video not ready")
        
    output_path = OUTPUTS_DIR / f"{job_id}.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="File missing")
        
    return FileResponse(output_path, media_type="video/mp4")

# UI Estática
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
