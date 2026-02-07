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

# Crear usuario
RUN useradd -m argos_user

# --- FIX CRÍTICO: CAMBIAR DUEÑO DE LA CARPETA ---
# Primero copiamos los archivos
COPY . .
# Luego le regalamos la carpeta al usuario para que pueda escribir
RUN chown -R argos_user:argos_user /app

# Cambiar al usuario (ahora sí tiene permisos)
USER argos_user

CMD ["python", "main.py"]