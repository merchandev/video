from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api import health, generation, jobs, files
from app.db.database import engine, Base
import os

# Inicializar Base de datos
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Local Video Studio (SkyReels)")

# Routers API
app.include_router(health.router, prefix="/api")
app.include_router(generation.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(files.router, prefix="/api")

# Montar UI Estática offline
os.makedirs("/app/static", exist_ok=True)
app.mount("/", StaticFiles(directory="/app/static", html=True), name="static")
