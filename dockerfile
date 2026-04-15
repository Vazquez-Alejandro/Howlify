# Usamos la imagen de Playwright para tener todos los navegadores listos
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Evita que Python genere archivos .pyc
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Instalamos Node.js (Necesario para Mudslide/WhatsApp)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# Copiamos e instalamos dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalamos los navegadores de Playwright por las dudas
RUN playwright install --with-deps chromium

# Copiamos todo el proyecto
COPY . .

# Exponemos el puerto
EXPOSE 8501

# Comando de arranque con los flags de seguridad para Render
CMD ["streamlit", "run", "app_dev.py", "--server.port", "8501", "--server.address", "0.0.0.0", "--server.enableCORS", "false", "--server.enableXsrfProtection", "false"]