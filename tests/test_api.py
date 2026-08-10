import pytest
from fastapi.testclient import TestClient
from app.main import app
import os
import tempfile
from PIL import Image
from unittest.mock import patch

client = TestClient(app)

import app.main

original_validate_model_integrity = app.main.validate_model_integrity

# Fixture global: solo mockea validator y queue_job. NO mockea Path.exists
# para que test_validate_model_integrity pueda usar el filesystem real.
@pytest.fixture(autouse=True)
def mock_model_files():
    with patch("app.main.validate_model_integrity", return_value=True), \
         patch("app.main.queue_job"):
        yield

# Fixture específico para tests /generate que necesitan que el modelo "exista"
@pytest.fixture
def mock_model_path_exists():
    with patch("app.main.Path.exists", return_value=True):
        yield


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_readiness_check():
    response = client.get("/api/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "gpu" in data
    assert "models" in data

def test_generate_t2v(mock_model_path_exists):
    response = client.post(
        "/api/generate",
        data={
            "mode": "t2v",
            "prompt": "Un perrito corriendo en el parque",
            "profile": "extreme",
            "duration_seconds": 2
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"

def test_generate_i2v_invalid_image():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"No soy una imagen")
        f.flush()
        with open(f.name, "rb") as file_to_upload:
            response = client.post(
                "/api/generate",
                data={"mode": "i2v", "prompt": "Anima esto"},
                files={"image": ("test.txt", file_to_upload, "text/plain")}
            )
            assert response.status_code == 400
    os.remove(f.name)

def test_generate_i2v_valid_image(mock_model_path_exists):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (100, 100), color="red")
        img.save(f, format="PNG")
        f.flush()
        with open(f.name, "rb") as file_to_upload:
            response = client.post(
                "/api/generate",
                data={"mode": "i2v", "prompt": "Anima esto", "profile": "extreme"},
                files={"image": ("test.png", file_to_upload, "image/png")}
            )
            assert response.status_code == 200
    os.remove(f.name)

def test_generate_invalid_mode():
    response = client.post(
        "/api/generate",
        data={
            "mode": "invalido",
            "prompt": "Test"
        }
    )
    assert response.status_code == 400
    assert "Modo inválido" in response.json()["detail"]

def test_generate_invalid_duration():
    response = client.post(
        "/api/generate",
        data={
            "mode": "t2v",
            "prompt": "Test",
            "duration_seconds": 100
        }
    )
    assert response.status_code == 400
    assert "duración" in response.json()["detail"].lower()

def test_generate_first_last_without_end_image(mock_model_path_exists):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (100, 100), color="red")
        img.save(f, format="PNG")
        f.flush()
        with open(f.name, "rb") as file_to_upload:
            response = client.post(
                "/api/generate",
                data={"mode": "first_last", "prompt": "Test"},
                files={"image": ("test.png", file_to_upload, "image/png")}
            )
            assert response.status_code == 400
            assert "end_image" in response.json()["detail"]
    os.remove(f.name)

def test_job_not_found():
    response = client.get("/api/jobs/inventado")
    assert response.status_code == 404

def test_validate_model_integrity():
    from pathlib import Path
    import json
    
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir)
        
        # Test 1: Empty directory should fail
        assert not original_validate_model_integrity(model_path, "df")
        
        # Create all required base files
        required = [
            "model_index.json",
            "transformer/config.json",
            "vae/diffusion_pytorch_model.safetensors",
            "tokenizer/special_tokens_map.json",
            "tokenizer/spiece.model",
            "tokenizer/tokenizer.json",
            "tokenizer/tokenizer_config.json",
            "scheduler/scheduler_config.json",
            "text_encoder/config.json",
        ]
        for req in required:
            file_path = model_path / req
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()
            
        # Also need unsharded files because we don't have indexes yet
        (model_path / "transformer/diffusion_pytorch_model.safetensors").touch()
        (model_path / "text_encoder/model.safetensors").touch()
            
        # Test 2: Valid unsharded DF model
        assert original_validate_model_integrity(model_path, "df")
        
        # Test 3: Valid I2V model (needs more files)
        assert not original_validate_model_integrity(model_path, "i2v")
        i2v_reqs = [
            "image_encoder/config.json",
            "image_encoder/model.safetensors",
            "image_processor/preprocessor_config.json"
        ]
        for req in i2v_reqs:
            file_path = model_path / req
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()
        assert original_validate_model_integrity(model_path, "i2v")
        
        # Test 4: Sharded index with missing shard
        os.remove(model_path / "transformer/diffusion_pytorch_model.safetensors")
        index_path = model_path / "transformer/diffusion_pytorch_model.safetensors.index.json"
        with open(index_path, "w") as f:
            json.dump({"weight_map": {"some_layer": "shard-00001.safetensors"}}, f)
        
        assert not original_validate_model_integrity(model_path, "df")
        
        # Test 5: Sharded index with present shard
        (model_path / "transformer/shard-00001.safetensors").touch()
        assert original_validate_model_integrity(model_path, "df")

def test_generate_storyboard_invalid_count():
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(f, format="PNG")
        f.flush()
        
        # 1 image -> should fail (needs >= 2)
        with open(f.name, "rb") as file_to_upload:
            response = client.post(
                "/api/generate",
                data={"mode": "storyboard", "prompt": "Transition"},
                files=[("storyboard_images", ("test1.png", file_to_upload, "image/png"))]
            )
            assert response.status_code == 400
            
    os.remove(f.name)

def test_generate_storyboard_valid(mock_model_path_exists):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f1, \
         tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f2:
        
        img = Image.new("RGB", (100, 100), color="red")
        img.save(f1, format="PNG")
        f1.flush()
        
        img2 = Image.new("RGB", (100, 100), color="blue")
        img2.save(f2, format="PNG")
        f2.flush()
        
        with open(f1.name, "rb") as file1, open(f2.name, "rb") as file2:
            response = client.post(
                "/api/generate",
                data={"mode": "storyboard", "prompt": "Red to Blue", "duration_seconds": 4},
                files=[
                    ("storyboard_images", ("test1.png", file1, "image/png")),
                    ("storyboard_images", ("test2.png", file2, "image/png"))
                ]
            )
            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data
            
    os.remove(f1.name)
    os.remove(f2.name)

def test_generate_storyboard_too_many_images():
    """21 imágenes deben ser rechazadas por el backend"""
    files = []
    tmp_paths = []
    try:
        for i in range(21):
            f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            img = Image.new("RGB", (10, 10), color=(i*10 % 255, 0, 0))
            img.save(f, format="PNG")
            f.close()
            tmp_paths.append(f.name)

        handles = [open(p, "rb") for p in tmp_paths]
        files = [("storyboard_images", (f"img{i}.png", h, "image/png")) for i, h in enumerate(handles)]
        response = client.post(
            "/api/generate",
            data={"mode": "storyboard", "prompt": "Too many"},
            files=files
        )
        for h in handles:
            h.close()
        assert response.status_code == 400
    finally:
        for p in tmp_paths:
            try:
                os.remove(p)
            except Exception:
                pass

