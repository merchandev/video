import os
import gc
import asyncio
import torch
import imageio
from diffusers.utils import load_image
from app.db.models import Job
from pathlib import Path
import subprocess

from app.skyreels_v2_infer.pipelines import (
    Image2VideoPipeline, 
    Text2VideoPipeline, 
    DiffusionForcingPipeline
)
from app.skyreels_v2_infer.pipelines.image2video_pipeline import resizecrop

I2V_MODEL_ID = os.environ.get("SKYREELS_I2V_MODEL_ID", "/models/SkyReels-V2-I2V-1.3B-540P-Diffusers")
DF_MODEL_ID = os.environ.get("SKYREELS_DF_MODEL_ID", "/models/SkyReels-V2-DF-1.3B-540P-Diffusers")
DEFAULT_OFFLOAD_MODE = os.environ.get("DEFAULT_OFFLOAD_MODE", "auto")

def run_skyreels_sync(job: Job):
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        offload = False
        if DEFAULT_OFFLOAD_MODE == "auto" and device == "cuda":
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            if vram_gb <= 8.5:
                offload = True
        elif DEFAULT_OFFLOAD_MODE == "force":
            offload = True
            
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
            
        seed = job.seed if job.seed != -1 else torch.randint(0, 1000000, (1,)).item()
        
        kwargs = {
            "prompt": job.prompt,
            "negative_prompt": job.negative_prompt,
            "num_frames": job.frames,
            "num_inference_steps": 30,
            "guidance_scale": 6.0,
            "shift": 8.0,
            "generator": torch.Generator(device=device).manual_seed(seed),
            "height": job.height,
            "width": job.width,
        }
        
        if job.mode == "i2v":
            pipe = Image2VideoPipeline(
                model_path=I2V_MODEL_ID, dit_path=I2V_MODEL_ID, use_usp=False, offload=offload
            )
            image = load_image(job.image_path).convert("RGB")
            image = resizecrop(image, job.height, job.width)
            kwargs["image"] = image
            
            with torch.cuda.amp.autocast(dtype=pipe.transformer.dtype), torch.no_grad():
                video_frames = pipe(**kwargs)[0]
                
        elif job.mode == "t2v":
            pipe = Text2VideoPipeline(
                model_path=DF_MODEL_ID, dit_path=DF_MODEL_ID, use_usp=False, offload=offload
            )
            with torch.cuda.amp.autocast(dtype=pipe.transformer.dtype), torch.no_grad():
                video_frames = pipe(**kwargs)[0]
                
        elif job.mode in ["first_last", "extend"]:
            pipe = DiffusionForcingPipeline(
                DF_MODEL_ID, dit_path=DF_MODEL_ID, device=torch.device("cuda"),
                weight_dtype=torch.bfloat16, use_usp=False, offload=offload
            )
            kwargs["overlap_history"] = job.overlap_history
            kwargs["addnoise_condition"] = job.addnoise_condition
            kwargs["base_num_frames"] = 97
            kwargs["ar_step"] = job.ar_step
            kwargs["causal_block_size"] = 1
            kwargs["fps"] = 24
            
            if job.mode == "extend":
                video_frames = pipe.extend_video(
                    prefix_video_path=job.video_path,
                    **kwargs
                )[0]
            else:
                image = load_image(job.image_path).convert("RGB")
                image = resizecrop(image, job.height, job.width)
                end_image = load_image(job.end_image_path).convert("RGB")
                end_image = resizecrop(end_image, job.height, job.width)
                kwargs["image"] = image
                kwargs["end_image"] = end_image
                with torch.cuda.amp.autocast(dtype=pipe.transformer.dtype), torch.no_grad():
                    video_frames = pipe(**kwargs)[0]
        
        del pipe
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
            
        raw_path = f"/app/data/outputs/{job.id}_raw.mp4"
        imageio.mimwrite(raw_path, video_frames, fps=24, quality=8, output_params=["-loglevel", "error"])
        
        final_path = f"/app/data/outputs/{job.id}.mp4"
        crf = os.environ.get("FFMPEG_CRF", "18")
        
        target_w, target_h = (1280, 720) if job.width > job.height else (720, 1280)
        
        cmd = [
            "ffmpeg", "-y", "-i", raw_path, 
            "-vf", f"scale={target_w}:{target_h}:flags=lanczos", 
            "-c:v", "libx264", "-crf", crf, "-preset", "slow", "-pix_fmt", "yuv420p", 
            final_path
        ]
        
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return False, f"FFmpeg Error: {proc.stderr}"
            
        if os.path.exists(raw_path):
            os.remove(raw_path)
        return True, None
        
    except Exception as e:
        return False, str(e)

async def generate_video_safe(job: Job):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, run_skyreels_sync, job)
