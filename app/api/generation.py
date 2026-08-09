import uuid
import os
import shutil
from fastapi import APIRouter, File, Form, UploadFile, BackgroundTasks, Depends
from typing import Optional
from app.db.database import get_db
from app.db.models import Job
from sqlalchemy.orm import Session
from app.services.image_service import save_and_verify_image
from app.inference_worker import queue_job
from pathlib import Path

router = APIRouter()
INPUTS_DIR = Path("/app/data/inputs")

@router.post("/generate")
async def generate(
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
    job_id = str(uuid.uuid4())
    image_path = None
    end_image_path = None
    video_path = None
    
    if image:
        image_path = await save_and_verify_image(f"{job_id}_start", image)
    if end_image:
        end_image_path = await save_and_verify_image(f"{job_id}_end", end_image)
    if video:
        video_path = str(INPUTS_DIR / f"{job_id}_ext.mp4")
        with open(video_path, "wb") as f:
            f.write(await video.read())
            
    frames = int(duration_seconds * 24)
    if frames > 97 and mode == "t2v":
        mode = "extend" # Auto fallback for long video
    
    # Internal resolution map based on profile
    if profile == "extreme":
        width, height = (640, 368) if orientation == "horizontal" else (368, 640)
    elif profile == "low":
        width, height = (768, 432) if orientation == "horizontal" else (432, 768)
    else: # native
        width, height = (960, 544) if orientation == "horizontal" else (544, 960)
    
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
        frames=frames,
        ar_step=ar_step,
        overlap_history=overlap_history,
        addnoise_condition=addnoise_condition,
        status="queued"
    )
    db.add(new_job)
    db.commit()
    
    # Cola nativa segura con Lock
    background_tasks.add_task(queue_job, job_id)
    
    return {"job_id": job_id, "status": "queued"}
