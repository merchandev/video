from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime
from .database import Base

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, index=True)
    status = Column(String, default="queued") # queued, processing, completed, failed, cancelled
    mode = Column(String, default="i2v") # t2v, i2v, first_last, extend
    prompt = Column(String)
    negative_prompt = Column(String, nullable=True)
    image_path = Column(String, nullable=True)
    end_image_path = Column(String, nullable=True)
    video_path = Column(String, nullable=True)
    storyboard_paths = Column(String, nullable=True) # JSON encoded list of paths
    output_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    seed = Column(Integer, default=-1)
    profile = Column(String, default="extreme")
    width = Column(Integer)
    height = Column(Integer)
    frames = Column(Integer)
    error = Column(String, nullable=True)
    
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, default=30)
    
    # Diffusion Forcing / Advanced
    ar_step = Column(Integer, default=0)
    overlap_history = Column(Integer, default=17)
    addnoise_condition = Column(Integer, default=20)
