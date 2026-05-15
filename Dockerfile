# Usamos la imagen completa de Python 3.12 (Debian Bookworm)
FROM python:3.12-bookworm

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# 1. Instalamos solo lo mínimo indispensable para empezar: Curl y Node
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 2. Instalamos las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 3. LA CLAVE: Playwright instala sus propias dependencias de sistema
RUN pip install playwright && \
    playwright install-deps chromium && \
    playwright install chromium

# 4. Copiamos el resto del proyecto
COPY . .

# Puerto para Streamlit
EXPOSE 8501

# Comando de arranque (usa start.sh para soportar modos: web, api, worker)
CMD ["bash", "start.sh"]