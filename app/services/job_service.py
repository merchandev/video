from sqlalchemy.orm import Session
from app.db.models import Job
import asyncio
from app.services.comfy_client import run_comfy_workflow
from app.db.database import SessionLocal

async def queue_comfyui_job(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or job.status == "cancelled":
            return
            
        job.status = "processing"
        db.commit()
        
        success, error_msg = await run_comfy_workflow(job)
        
        if success:
            job.status = "completed"
        else:
            job.status = "failed"
            job.error = error_msg
            
        db.commit()
    except Exception as e:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error = str(e)
            db.commit()
    finally:
        db.close()
