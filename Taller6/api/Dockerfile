FROM python:3.11-slim

# Crear directorio de trabajo
WORKDIR /api

# Copiar los archivos necesarios manteniendo la estructura simple
COPY . /api/

# Actualizar pip y setuptools
RUN pip install --upgrade pip setuptools wheel

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Ejecutar entrenamiento
RUN python train_model.py

# Configurar para ejecución
WORKDIR /api/app

# Iniciar uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8989"]