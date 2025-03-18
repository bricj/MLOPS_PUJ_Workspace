# TALLER MLFLOW #

## Configuración del entorno de trabajo :wrench: ##

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

3. **jupyterlab:**
   -  para subir el servicio de *jupyterlab* accede a la carpeta *jupyter_api* y ejecuta el archivo .yaml usando el comando ```docker compose up -build ``` desde la terminal.
   - accede al link que aparecerá en la terminal una vez se haya creado el contenedor.

## Entrenamiento del modelo y captura de información :computer: ##

Para encontrar el notebook base de este ejercicio dirígete a la carpeta jupyter_api  --> jupyter_models --> app --> train_models.ipynb. Dentro del notebook se ejecutan los siguientes pasos:
- Creación de tablas dentro de la base de datos *mysql*
- carga de datos crudos a *mysql*
- Preprocesamiento de datos
- Entrenamiento de modelos (sin usar conexión a MLFow)
- Entrenamiento de modelos utilizando MLFlow:
  - Configuración de variables de entorno que apuntan al servicio de *MLFlow*
  - Aquí se configura una ejecución que varía 4 veces el hiperparámetro *C* y 5 veces el parámetro *gamma* para un modelo *SVM* para un total de 20 combinaciones.
  - Configuración de variables de entorno que apuntan al servicio *minio*
  - Creación cliente *minio*.
  - Paso a producción del mejor modelo *SVM* encontrado (este paso se realiza en la interfaz de *mlflow*).
  - Request al modelo productivo disponible en *mlflow* para verificar funcionamiento. 

