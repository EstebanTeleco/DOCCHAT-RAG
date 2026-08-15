# Imagen base ligera de Python
FROM python:3.11-slim

WORKDIR /app

# Instala dependencias del sistema necesarias para pdfplumber
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia solo requirements primero (aprovecha cache de Docker: si no cambian
# las dependencias, no las reinstala en cada build)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código
COPY . .

# Puertos que usan la API (8000) y el frontend (8501)
EXPOSE 8000 8501
