
# Proyecto No. 3

A continuacion se presenta el desarrollo del proyecto 3, donde se ha implementado un flujo de MLOps para la inferencia de un modelo de clasificacion. Los servicios utilizados en el back son PostgreSQL, FASTAPI, Minio, Airflow, Mlflow y Locust. Para la seccion del front se han utilizado Prometheus y Grafana. 

## 1. Servicios

### 1.0 Orquestacion y administracion de servicios

Los servicios seran orquestados con Airflow a traves de la ejecucion secuencial de dags. 

Por su parte, el servicio de Airflow sera administrado con docker compose, mientras que los servicios restantes seran adminsitrados con kubernetes.

En una posterior seccion se detallara la configuracion del Airflow y Kubernetes.

### 1.1 Dataset

Los datos que se procesaran y sobre el cual se realizaran inferencias de un modelo de clasificacion es Diabetes 130-US Hospitals for Years 1999-2008 (https://archive.ics.uci.edu/dataset/296/diabetes+130-us+hospitals+for+years+1999-2008). El dataset esta compuesto por variables categoricas y cuantitativas. Para disponibilizar los datos, se ha levantado un servicio en FASTAPI.

Teniendo en cuenta los requisitos del proyecto, los datos se han particionado en datos de entrenamiento, validacion y evaluacion. Los datos se cargan por batch de 15000 registros, por consiguiente, se han definido endpoints para obtener el numero de batches para cada particion. Asi mismo, se han definido controles para dar seguimiento a los datos procesados.




* Hay un jupyter en la carpeta airflow, donde se hicieron pruebas y validacion de datos.


* La base de Minio es el mismo sql utilizado en anteriores talleres, las credeniales estan en el taller 3 o 4 (readme)


* Se deben crear la conexiones a la base de datos de diabetes (puerto 3307):

La base de datos diabetes contiene los datos crudos y los datos procesados (clean)

conn id: mysql_diabetes_conn

conn type: MySQL

host: mysql_diabetes

schema: diabetes

login: diabetes_user

password: diabetes_password

port: 3307

el archivo sql de raw data esta en la carpeta raw data


* Se estan utilizando la redes:

docker network create proyecto2_airflow_network

docker network create --driver bridge my_shared_network

* Orden de los dags

1. iniciar_tabla_mysql: borra o crea la tabla sql

2. fetch_and_store_diabetes_data: almacena la data cruda, la consume de un fastapi (puerto 80)

3. diabetes_etl_fast: lee los datos por batch, genera tres tablas: train, validation y test (batch de 15000 registros)

4. diabetes_model_pipeline: limpieza de datos, procesamiento y almacenamiento de data limpia

