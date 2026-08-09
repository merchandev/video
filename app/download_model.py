import os
from huggingface_hub import snapshot_download

def download_wan_model():
    model_id = "Wan-AI/Wan2.2-TI2V-5B"
    # Fallback to Wan-AI/Wan2.1-TI2V-14B if 2.2 is not found, but we will try 2.2 first
    
    output_dir = os.environ.get("MODEL_DIR", "/models/Wan2.2-TI2V-5B")
    
    print(f"Descargando {model_id} en {output_dir}...")
    
    try:
        snapshot_download(
            repo_id=model_id,
            local_dir=output_dir,
            local_dir_use_symlinks=False
        )
        print("¡Descarga completada!")
    except Exception as e:
        print(f"Error descargando el modelo {model_id}: {e}")
        print("Intentando descargar Wan2.1 como fallback...")
        try:
            snapshot_download(
                repo_id="Wan-AI/Wan2.1-I2V-14B-480P", # Fallback example
                local_dir=output_dir,
                local_dir_use_symlinks=False
            )
            print("¡Descarga de fallback completada!")
        except Exception as e2:
            print(f"Error en fallback: {e2}")

if __name__ == "__main__":
    download_wan_model()
