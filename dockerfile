# Usamos Python 3.12 oficial como base
FROM python:3.12-slim

# Evita archivos .pyc y trabas en el buffer
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Instalamos dependencias de sistema necesarias para Playwright y Node
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    libgconf-2-4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    libgbm-dev \
    libnss3 \
    libxss1 \
    libasound2 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Actualizamos pip e instalamos las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Instalamos Playwright y sus navegadores
RUN pip install playwright && \
    playwright install --with-deps chromium

# Copiamos el resto del proyecto
COPY . .

EXPOSE 8501

# Comando de arranque para Render
CMD ["streamlit", "run", "app_dev.py", "--server.port", "8501", "--server.address", "0.0.0.0", "--server.enableCORS", "false", "--server.enableXsrfProtection", "false"]