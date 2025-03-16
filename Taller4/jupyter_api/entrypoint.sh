#!/bin/bash

# Obtener la IP de la máquina anfitriona en la interfaz principal
HOST_IP=$(hostname -I | awk '{print $1}')

# Exportar la variable con la IP obtenida
export MLFLOW_S3_ENDPOINT_URL="http://$HOST_IP:9000"

echo "Usando MLFLOW_S3_ENDPOINT_URL=$MLFLOW_S3_ENDPOINT_URL"

# Iniciar Jupyter Lab
exec jupyter lab --ip=0.0.0.0 --allow-root