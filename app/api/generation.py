import uuid
import os
from fastapi import APIRouter, File, Form, UploadFile, BackgroundTasks, Depends
from typing import Optional
from app.db.database import get_db
from app.db.models import Job
from sqlalchemy.orm import Session
from app.services.image_service import save_and_verify_image
from app.services.job_service import queue_comfyui_job

router = APIRouter()

@router.post("/generate")
async def generate(
    background_tasks: BackgroundTasks,
    prompt: str = Form(...),
    image: Optional[UploadFile] = File(None),
    orientation: str = Form("horizontal"),
    duration_seconds: int = Form(5),
    seed: int = Form(-1),
    sample_steps: int = Form(50),
    guide_scale: float = Form(5.0),
    sample_solver: str = Form("unipc"),
    db: Session = Depends(get_db)
):
    job_id = str(uuid.uuid4())
    image_path = None
    
    if image:
        image_path = await save_and_verify_image(job_id, image)
        
    # Calcular frames (4n+1)
    target = duration_seconds * 24
    n = round((target - 1) / 4)
    frame_num = max(1, (4 * n) + 1)
    
    width = 704 if orientation == "vertical" else 1280
    height = 1280 if orientation == "vertical" else 704
    
    new_job = Job(
        id=job_id,
        prompt=prompt,
        image_path=image_path,
        seed=seed,
        width=width,
        height=height,
        frames=frame_num,
        status="queued"
    )
    db.add(new_job)
    db.commit()
    
    # Encolar a ComfyUI
    background_tasks.add_task(queue_comfyui_job, job_id)
    
    return {"job_id": job_id, "status": "queued"}
