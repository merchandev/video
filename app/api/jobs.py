from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Job
from fastapi.responses import JSONResponse
import httpx

router = APIRouter()

@router.get("/jobs/{job_id}")
async def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JSONResponse(status_code=404, content={"error": "Not found"})
        
    progress = 0.0
    if job.status == "processing":
        try:
            async with httpx.AsyncClient() as client:
                progress = 0.5 # Mock, se integraría con ComfyUI /queue
        except:
            pass
    elif job.status == "completed":
        progress = 1.0
        
    return {
        "id": job.id,
        "status": job.status,
        "progress": progress,
        "video_url": f"/api/files/outputs/{job_id}.mp4" if job.status == "completed" else None,
        "error": job.error,
        "params": {
            "prompt": job.prompt,
            "seed": job.seed
        }
    }

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JSONResponse(status_code=404, content={"error": "Not found"})
        
    if job.status in ["queued", "processing"]:
        job.status = "cancelled"
        db.commit()
        # Aquí se enviaría la orden de interrupción a ComfyUI
        
    return {"status": "cancelled"}
