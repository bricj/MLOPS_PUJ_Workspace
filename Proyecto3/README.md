
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

***** Incluir imagen del servicio de fastapi ******

### 1.2 Airflow

El servicio de airflow se levanta por medio de docker compose, por consiguiente es necesario ubicarse en la carpeta que contiene el archivo .yaml con la configuracion de docker:

```cd /Proyecto3/model_training```

Antes de levantar el servicio del contendor, se recomienda crear las redes de docker:

```sudo docker network create proyecto2_airflow_network```
```sudo docker network create --driver bridge my_shared_network```

Se procede a levantar el servicio de Airflow.

```sudo docker compose up --build```

Se accede a airflow con las credenciales:

user: airflow
password: airflow

En primera instancia es necesario crear la conexion a la base de datos diabetes:

En el menu de Airflow, se ingresa en Admin -> Connections

***** Imagen airflow ******

conn id: postgres_airflow_conn

conn type: Postgres

host: 10.43.101.168

database: airflow

login: airflow

password: airflow_pass

port: 32148

La orquestacion a traves de Airflow se realiza a traves de DAGs, por consiguiente, se han creado las siguientes etapas en el proceso:

* 1.2.1 DAG: mysql_start_table.py - iniciar_tabla_mysql
  
Se encarga de la validacion y creacion de la tabla de datos PostgreSQL para almacenar los datos obtenidos mediantes batch del FASTAPI que contiene la tabla de datos Diabetes. Es importante mencionar que la tabla de datos se ha disponibilizado mediante kubernetes, por ello, en la siguiente etapa se consume la IP:puerto generada dicho servicio.

* 1.2.2 DAG: fetch_and_store_data.py - fetch_and_store_diabetes_data

Se ejecuta la consulta al endpoint que contiene la informacion del dataset Diabetes. Importante mencionar que la obtencion de informacion se realiza por batch y para cada particion de datos. Asi mismo, se crean tablas de datos para entrenamiento, validacion y evaluacion en la base de datos.

********* Incluir imagen del DAG*******

* 1.2.3 DAG: preprocess.py - diabetes_etl_fast








el archivo sql de raw data esta en la carpeta raw data


* Se estan utilizando la redes:





* Orden de los dags

1. iniciar_tabla_mysql: borra o crea la tabla sql

2. fetch_and_store_diabetes_data: almacena la data cruda, la consume de un fastapi (puerto 80)

3. diabetes_etl_fast: lee los datos por batch, genera tres tablas: train, validation y test (batch de 15000 registros)

4. diabetes_model_pipeline: limpieza de datos, procesamiento y almacenamiento de data limpia

