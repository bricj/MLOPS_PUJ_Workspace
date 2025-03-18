## TALLER MLFLOW ##

En este ejercicio se comunican vía internet 4 servicios distintos:
- Una base de datos de mysql
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
   - una vez dentro de la plataforma crea un nuevo contenedor con el nombre **mlflows3**. En este contenedor se almacenarán los artefactos que se creen en *MLFlow*