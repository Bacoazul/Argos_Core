# Base image
FROM python:3.12-slim

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Instalar git
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install -r requirements.txt

# Crear usuario y directorios de datos persistentes
RUN useradd -m argos_user && \
    chown -R argos_user:argos_user /app && \
    mkdir -p /data/argos && \
    chown -R argos_user:argos_user /data

# Copiar código y ajustar permisos
COPY . .
RUN chown -R argos_user:argos_user /app

# Cambiar al usuario
USER argos_user

CMD ["python", "main.py"]
