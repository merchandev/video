import asyncio
from app.db.database import SessionLocal
from app.db.models import Job
from app.model_manager import generate_video_safe

gpu_lock = asyncio.Lock()

async def queue_job(job_id: str):
    async with gpu_lock:
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job or job.status == "cancelled":
                return
                
            job.status = "processing"
            db.commit()
            
            # Ejecutar inferencia
            success, error_msg = await generate_video_safe(job_id)
            
            # Recargar objeto db que se quedó viejo
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
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
