import os
import sys
from huggingface_hub import snapshot_download

def download_models():
    model_dir = os.environ.get("MODEL_DIR", "/models/Wan2.2-TI2V-5B")
    model_id = "Wan-AI/Wan2.2-TI2V-5B"
    
    print(f"Descargando {model_id} en {model_dir}...")
    try:
        snapshot_download(
            repo_id=model_id,
            local_dir=model_dir,
            local_dir_use_symlinks=False
        )
        print("¡Descarga completada con éxito!")
    except Exception as e:
        print(f"Error fatal descargando el modelo: {e}")
        print("Reintenta cuando tengas conexión estable.")
        sys.exit(1) # Salida con error intencional sin fallback

if __name__ == "__main__":
    download_models()
