import os
import sys
from huggingface_hub import snapshot_download

def download_models():
    model_dir_base = os.environ.get("MODEL_DIR_BASE", "/models")
    
    models = {
        "Skywork/SkyReels-V2-I2V-1.3B-540P-Diffusers": os.path.join(model_dir_base, "SkyReels-V2-I2V-1.3B-540P-Diffusers"),
        "Skywork/SkyReels-V2-DF-1.3B-540P-Diffusers": os.path.join(model_dir_base, "SkyReels-V2-DF-1.3B-540P-Diffusers")
    }
    
    for model_id, local_dir in models.items():
        print(f"Descargando {model_id} en {local_dir}...")
        try:
            snapshot_download(
                repo_id=model_id,
                local_dir=local_dir,
                local_dir_use_symlinks=False
            )
            print(f"¡Descarga de {model_id} completada con éxito!")
        except Exception as e:
            print(f"Error fatal descargando {model_id}: {e}")
            print("Reintenta cuando tengas conexión estable.")
            sys.exit(1)

if __name__ == "__main__":
    download_models()
