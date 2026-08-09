FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

# Fijamos una versión específica de ComfyUI (tag/commit si fuera necesario)
RUN git clone https://github.com/comfyanonymous/ComfyUI.git comfyui

WORKDIR /opt/comfyui
RUN pip install --no-cache-dir -r requirements.txt

# Instalar nodos extra si se requiere para Wan2.2 (ej. ComfyUI-VideoHelperSuite)
RUN cd custom_nodes && git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && cd ComfyUI-VideoHelperSuite && pip install --no-cache-dir -r requirements.txt

EXPOSE 8188

CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188", "--preview-method", "auto"]
