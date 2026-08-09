import pytest
from fastapi.testclient import TestClient
from app.main import app
import os
import tempfile
from PIL import Image
from unittest.mock import patch

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_model_files():
    with patch("app.main.validate_model_integrity", return_value=True), \
         patch("app.main.queue_job"), \
         patch("app.main.Path.exists", return_value=True):
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

def test_generate_t2v():
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

def test_generate_i2v_valid_image():
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

def test_generate_first_last_without_end_image():
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
