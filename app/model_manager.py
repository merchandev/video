import os
import gc
import asyncio
import torch
import imageio
from diffusers.utils import load_image, load_video
from diffusers import (
    SkyReelsV2ImageToVideoPipeline,
    SkyReelsV2DiffusionForcingPipeline,
    SkyReelsV2DiffusionForcingImageToVideoPipeline,
    SkyReelsV2DiffusionForcingVideoToVideoPipeline,
    AutoencoderKLWan,
    UniPCMultistepScheduler,
)
from app.db.models import Job
from app.db.database import SessionLocal
import subprocess

I2V_MODEL_ID = os.environ.get("SKYREELS_I2V_MODEL_ID", "/models/SkyReels-V2-I2V-1.3B-540P-Diffusers")
DF_MODEL_ID = os.environ.get("SKYREELS_DF_MODEL_ID", "/models/SkyReels-V2-DF-1.3B-540P-Diffusers")
DEFAULT_OFFLOAD_MODE = os.environ.get("DEFAULT_OFFLOAD_MODE", "auto")

def run_skyreels_sync(job_id: str):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return False, "Job not found"
        
    def progress_callback(pipe, step, timestep, callback_kwargs):
        db.refresh(job)
        if job.status == "cancelled":
            raise Exception("Job cancelled by user")
        job.current_step = step
        db.commit()
        return callback_kwargs

    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        offload = False
        OFFLOAD_THRESHOLD_GB = float(os.getenv("OFFLOAD_THRESHOLD_GB", "16"))
        if DEFAULT_OFFLOAD_MODE == "auto" and device == "cuda":
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            if vram_gb < OFFLOAD_THRESHOLD_GB:
                offload = True
        elif DEFAULT_OFFLOAD_MODE == "force":
            offload = True
            
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
            
        seed = job.seed if job.seed != -1 else torch.randint(0, 1000000, (1,)).item()
        if job.seed == -1:
            job.seed = seed
            db.commit()
        
        kwargs = {
            "prompt": job.prompt,
            "negative_prompt": job.negative_prompt,
            "num_frames": job.frames,
            "num_inference_steps": 30,
            "guidance_scale": 6.0 if job.mode == "t2v" else 5.0,
            "generator": torch.Generator(device=device).manual_seed(seed),
            "height": job.height,
            "width": job.width,
            "callback_on_step_end": progress_callback
        }
        
        if job.profile == "extreme":
            base_num_frames = 57
        elif job.profile == "low":
            base_num_frames = 77
        else:
            base_num_frames = 97
        # Parámetros avanzados para el modelo
        kwargs["base_num_frames"] = base_num_frames
        kwargs["ar_step"] = job.ar_step
        kwargs["causal_block_size"] = 5 if job.ar_step > 0 else None
        kwargs["overlap_history"] = job.overlap_history if job.frames > base_num_frames else None
        kwargs["addnoise_condition"] = job.addnoise_condition

        
        if job.mode == "i2v":
            if job.frames > 97:
                vae = AutoencoderKLWan.from_pretrained(
                    DF_MODEL_ID,
                    subfolder="vae",
                    torch_dtype=torch.float32,
                    local_files_only=True,
                    use_safetensors=True,
                )
                pipe = SkyReelsV2DiffusionForcingImageToVideoPipeline.from_pretrained(
                    DF_MODEL_ID, 
                    vae=vae,
                    torch_dtype=torch.bfloat16,
                    use_safetensors=True,
                    local_files_only=True
                )
                pipe.scheduler = UniPCMultistepScheduler.from_config(
                    pipe.scheduler.config,
                    flow_shift=5.0,
                )
            else:
                vae = AutoencoderKLWan.from_pretrained(
                    I2V_MODEL_ID,
                    subfolder="vae",
                    torch_dtype=torch.float32,
                    local_files_only=True,
                    use_safetensors=True,
                )
                pipe = SkyReelsV2ImageToVideoPipeline.from_pretrained(
                    I2V_MODEL_ID, 
                    vae=vae,
                    torch_dtype=torch.bfloat16,
                    use_safetensors=True,
                    local_files_only=True
                )
                pipe.scheduler = UniPCMultistepScheduler.from_config(
                    pipe.scheduler.config,
                    flow_shift=5.0,
                )
            
            if offload:
                pipe.enable_sequential_cpu_offload()
            else:
                pipe.to(device)
                
            image = load_image(job.image_path).convert("RGB")
            kwargs["image"] = image
            
            # Remover parametros que I2V estándar podría no soportar en Diffusers base
            if job.frames <= 97:
                kwargs.pop("ar_step", None)
                kwargs.pop("causal_block_size", None)
                kwargs.pop("overlap_history", None)
                kwargs.pop("addnoise_condition", None)
                kwargs.pop("base_num_frames", None)
            
            # Use diffusers native precision management
            video_frames = pipe(**kwargs).frames[0]
                
        elif job.mode == "t2v":
            vae = AutoencoderKLWan.from_pretrained(
                DF_MODEL_ID,
                subfolder="vae",
                torch_dtype=torch.float32,
                local_files_only=True,
                use_safetensors=True,
            )
            pipe = SkyReelsV2DiffusionForcingPipeline.from_pretrained(
                DF_MODEL_ID,
                vae=vae,
                torch_dtype=torch.bfloat16,
                use_safetensors=True,
                local_files_only=True
            )
            pipe.scheduler = UniPCMultistepScheduler.from_config(
                pipe.scheduler.config,
                flow_shift=8.0,
            )
            
            if offload:
                pipe.enable_sequential_cpu_offload()
            else:
                pipe.to(device)
                
            # Use diffusers native precision management
            video_frames = pipe(**kwargs).frames[0]
                
        elif job.mode == "first_last":
            vae = AutoencoderKLWan.from_pretrained(
                DF_MODEL_ID,
                subfolder="vae",
                torch_dtype=torch.float32,
                local_files_only=True,
                use_safetensors=True,
            )
            pipe = SkyReelsV2DiffusionForcingImageToVideoPipeline.from_pretrained(
                DF_MODEL_ID, 
                vae=vae,
                torch_dtype=torch.bfloat16,
                use_safetensors=True,
                local_files_only=True
            )
            pipe.scheduler = UniPCMultistepScheduler.from_config(
                pipe.scheduler.config,
                flow_shift=5.0,
            )
            
            if offload:
                pipe.enable_sequential_cpu_offload()
            else:
                pipe.to(device)
                
            from PIL import Image, ImageOps
            target_size = (job.width, job.height)
            image = load_image(job.image_path).convert("RGB")
            last_image = load_image(job.end_image_path).convert("RGB")
            if image.size != target_size:
                image = ImageOps.fit(image, target_size, method=Image.Resampling.LANCZOS)
            if last_image.size != target_size:
                last_image = ImageOps.fit(last_image, target_size, method=Image.Resampling.LANCZOS)
            kwargs["image"] = image
            kwargs["last_image"] = last_image
            
            # Use diffusers native precision management
            video_frames = pipe(**kwargs).frames[0]
                
        elif job.mode == "extend":
            vae = AutoencoderKLWan.from_pretrained(
                DF_MODEL_ID,
                subfolder="vae",
                torch_dtype=torch.float32,
                local_files_only=True,
                use_safetensors=True,
            )
            pipe = SkyReelsV2DiffusionForcingVideoToVideoPipeline.from_pretrained(
                DF_MODEL_ID, 
                vae=vae,
                torch_dtype=torch.bfloat16,
                use_safetensors=True,
                local_files_only=True
            )
            pipe.scheduler = UniPCMultistepScheduler.from_config(
                pipe.scheduler.config,
                flow_shift=5.0,
            )
            
            if offload:
                pipe.enable_sequential_cpu_offload()
            else:
                pipe.to(device)
                
            video_input = load_video(job.video_path)
            kwargs["video"] = video_input
            
            # Use diffusers native precision management
            video_frames = pipe(**kwargs).frames[0]
            
        elif job.mode == "storyboard":
            import json
            import numpy as np
            items = json.loads(job.storyboard_paths) if job.storyboard_paths else []
            if len(items) < 2:
                raise Exception("Not enough items for storyboard")
            
            # Normalize: support both old string format and new {type,path} dict format
            def normalize_item(x):
                if isinstance(x, str):
                    return {"type": "image", "path": x}
                return x

            items = [normalize_item(x) for x in items]
                
            vae = AutoencoderKLWan.from_pretrained(
                DF_MODEL_ID,
                subfolder="vae",
                torch_dtype=torch.float32,
                local_files_only=True,
                use_safetensors=True,
            )
            pipe = SkyReelsV2DiffusionForcingImageToVideoPipeline.from_pretrained(
                DF_MODEL_ID, 
                vae=vae,
                torch_dtype=torch.bfloat16,
                use_safetensors=True,
                local_files_only=True
            )
            pipe.scheduler = UniPCMultistepScheduler.from_config(
                pipe.scheduler.config,
                flow_shift=5.0,
            )
            
            if offload:
                pipe.enable_sequential_cpu_offload()
            else:
                pipe.to(device)
                
            from PIL import Image, ImageOps
            all_video_frames = []
            base_size = (job.width, job.height)

            def fit_img(img):
                """Resize + crop to base_size preserving aspect ratio."""
                if img.size != base_size:
                    return ImageOps.fit(img, base_size, method=Image.Resampling.LANCZOS)
                return img

            def load_as_frames(item):
                """Return a list of numpy uint8 frames for any item."""
                if item["type"] == "video":
                    reader = imageio.get_reader(item["path"])
                    raw_frames = [frame for frame in reader]
                    reader.close()
                    # Resize every frame to base_size
                    result = []
                    for f in raw_frames:
                        pil = Image.fromarray(f).convert("RGB")
                        pil = fit_img(pil)
                        result.append(np.array(pil))
                    return result
                else:
                    pil = load_image(item["path"]).convert("RGB")
                    pil = fit_img(pil)
                    return [np.array(pil)]  # single frame

            def last_pil(item):
                """Get last PIL frame of an item (for transition start)."""
                if item["type"] == "video":
                    reader = imageio.get_reader(item["path"])
                    last = None
                    for frame in reader:
                        last = frame
                    reader.close()
                    if last is None:
                        raise Exception(f"Video vacío: {item['path']}")
                    pil = Image.fromarray(last).convert("RGB")
                    return fit_img(pil)
                else:
                    pil = load_image(item["path"]).convert("RGB")
                    return fit_img(pil)

            def first_pil(item):
                """Get first PIL frame of an item (for transition end)."""
                if item["type"] == "video":
                    reader = imageio.get_reader(item["path"])
                    first = next(iter(reader))
                    reader.close()
                    pil = Image.fromarray(first).convert("RGB")
                    return fit_img(pil)
                else:
                    pil = load_image(item["path"]).convert("RGB")
                    return fit_img(pil)

            def run_ai_transition(start_pil, end_pil, pair_idx, total_pairs, ai_step_offset, total_ai_steps):
                """Run AI interpolation between two PIL images."""
                def sb_progress_callback(pipe, step, timestep, callback_kwargs, _offset=ai_step_offset):
                    db.refresh(job)
                    if job.status == "cancelled":
                        raise Exception("Job cancelled by user")
                    job.current_step = _offset + step
                    db.commit()
                    return callback_kwargs

                kwargs["image"] = start_pil
                kwargs["last_image"] = end_pil
                kwargs["callback_on_step_end"] = sb_progress_callback
                return pipe(**kwargs).frames[0]

            # Count how many AI transitions we'll need
            ai_transitions = 0
            for i in range(len(items) - 1):
                a, b = items[i], items[i+1]
                # AI is needed between image→image, image→video, video→image, video→video (boundary)
                # We always generate a transition at every boundary for consistency
                ai_transitions += 1

            job.total_steps = 30 * ai_transitions
            db.commit()

            ai_step_offset = 0
            is_first_segment = True

            for i in range(len(items) - 1):
                a, b = items[i], items[i+1]

                # 1. Include raw frames of item A (if it's a video and we haven't added it yet)
                if a["type"] == "video":
                    a_frames = load_as_frames(a)
                    if is_first_segment:
                        all_video_frames.extend(a_frames)
                    else:
                        all_video_frames.extend(a_frames[1:])  # skip duplicate frame at join
                    is_first_segment = False
                elif is_first_segment and a["type"] == "image":
                    # For pure image storyboards: the transition starts at this image —
                    # don't pre-add it; AI will produce the first frame
                    pass

                # 2. Generate AI transition from last frame of A → first frame of B
                start_pil = last_pil(a)
                end_pil = first_pil(b)
                transition = run_ai_transition(start_pil, end_pil, i, ai_transitions, ai_step_offset, 30 * ai_transitions)
                ai_step_offset += 30

                # For image→image: transition IS the segment (no pre-added frames)
                # For video→*: skip frame[0] because it duplicates last raw frame
                if a["type"] == "video":
                    all_video_frames.extend(transition[1:])
                else:
                    if is_first_segment:
                        all_video_frames.extend(transition)
                        is_first_segment = False
                    else:
                        all_video_frames.extend(transition[1:])

                # 3. If B is a video and it's the last item, add its raw frames
                #    (if B is not the last item, it will be handled as A in the next iteration)
                if b["type"] == "video" and i == len(items) - 2:
                    b_frames = load_as_frames(b)
                    all_video_frames.extend(b_frames[1:])

            video_frames = all_video_frames
        
        del pipe
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
            
        DATA_DIR = os.getenv("DATA_DIR", "/app/data")
        raw_path = f"{DATA_DIR}/outputs/{job.id}_raw.mp4"
        imageio.mimwrite(raw_path, video_frames, fps=24, quality=8, output_params=["-loglevel", "error"])
        
        final_path = f"{DATA_DIR}/outputs/{job.id}.mp4"
        crf = os.environ.get("FFMPEG_CRF", "18")
        
        target_w, target_h = (1280, 720) if job.width > job.height else (720, 1280)
        
        cmd = [
            "ffmpeg", "-y", "-i", raw_path, 
            "-vf", f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h}", 
            "-c:v", "libx264", "-crf", crf, "-preset", "slow", "-pix_fmt", "yuv420p", 
            final_path
        ]
        
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            db.close()
            return False, f"FFmpeg Error: {proc.stderr}"
            
        if os.path.exists(raw_path):
            os.remove(raw_path)
            
        db.close()
        return True, None
        
    except Exception as e:
        db.close()
        return False, str(e)

async def generate_video_safe(job_id: str):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, run_skyreels_sync, job_id)
