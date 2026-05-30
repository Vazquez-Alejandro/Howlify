# Usamos la imagen completa de Python 3.12 (Debian Bookworm)
FROM python:3.12-bookworm

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# 1. Instalamos dependencias de sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# 2. Instalamos las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 3. Playwright (solo chromium)
RUN pip install playwright && \
    playwright install-deps chromium && \
    playwright install chromium

# 4. Copiamos el resto del proyecto
COPY . .

# Puerto para la API
EXPOSE 8000

# Comando de arranque (usa start.sh para soportar modos: web, api, worker)
CMD ["bash", "start.sh"]