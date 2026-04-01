FROM mcr.microsoft.com/playwright/python:v1.48.0-noble

WORKDIR /app

# Instala dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código
COPY . .

# Expone puerto y arranca
EXPOSE 8501
CMD ["streamlit", "run", "app_dev.py", "--server.port", "8501", "--server.address", "0.0.0.0"]