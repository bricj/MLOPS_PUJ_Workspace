## TALLER MLFLOW ##

En este ejercicio se comunican vía internet 3 servicios distintos:
- Un bucket de Minio (puerto 9000)
- Un entorno jupyter lab (puerto )
- MLFlow (puerto )

Para ejecutar adecuadamente los 3 servicios sigue estos pasos:
1. **Minio & mysql:**
   - abre una terminal en el directorio *mysql_minio* y ejecuta el archivo .yaml usando el comando ```docker compose up -d ```
   - accede al servicio minio usando el enlace ``` http://localhost:9000```
   - ingresa las credenciales para acceder a minio:
     - **usuario:** admin
     - **contraseña:** supersecret
   - una vez dentro de la plataforma crea un nuevo bucket con el nombre **mlflows3**. En este contenedor se almacenarán los artefactos que se creen en *MLFlow*.
   - Asegurate de dejar encendidos todos los interruptores al configurar el bucket.

2. **MLFlow:**
   - ingresa al directorio *mlflow* y abre en el editor el archivo *mlflow_service.service*
   - edita la variable *WorkingDirectory* con las ruta a las carpeta donde clonaste este repositorio.
   - reemplaza en las variables *MLFLOW_S3_ENDPOINT_URL* y *backend-store-uri* la IP por la IP de tu máquina.
   - refresca el daemon usando en terminal el comando ``` sudo systemctl daemon-reload ```
   - Habilita y valida el servicio utilizando ```sudo systemctl enable /ruta-a-la-carpeta-mlflow/mlflow_serv.service ``` y ```sudo systemctl start mlflow_serv.service ```.
   - verifica que *mlflow* está corriendo usando el comando ```sudo systemctl status mlflow_serv.service ```.
   - ingresa a tu navegador a la dirección ``` http://localhost:5000```. Allí te deberá cargar la interfaz de *mlflow*.