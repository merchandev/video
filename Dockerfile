FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-devel

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    wget \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar requerimientos primero para aprovechar la caché de Docker
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Opcional: instalar flash-attention
ARG INSTALL_FLASH_ATTN=0
RUN if [ "$INSTALL_FLASH_ATTN" = "1" ] ; then \
      pip install --no-cache-dir flash-attn --no-build-isolation ; \
    fi

# Copiar el resto del código
COPY app /app

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
