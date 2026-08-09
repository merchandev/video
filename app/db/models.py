from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime
from .database import Base

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, index=True)
    status = Column(String, default="queued") # queued, processing, completed, failed, cancelled
    prompt = Column(String)
    image_path = Column(String, nullable=True)
    output_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    seed = Column(Integer, default=-1)
    width = Column(Integer)
    height = Column(Integer)
    frames = Column(Integer)
    error = Column(String, nullable=True)
