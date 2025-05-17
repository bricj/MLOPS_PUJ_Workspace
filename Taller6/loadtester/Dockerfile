
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements.txt primero para aprovechar la caché de Docker
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el archivo locust.py
COPY locust.py .

# Exponer el puerto de la interfaz web de Locust
EXPOSE 8089

# Variables de entorno que serán sobrescritas en el deployment de Kubernetes
ENV TARGET_HOST="http://fastapi-inference-service:8989"
ENV LOCUST_LOCUSTFILE="/app/locust.py"
ENV PYTHONUNBUFFERED=1

# Comando para iniciar Locust
CMD ["locust", "--host", "${TARGET_HOST}"]