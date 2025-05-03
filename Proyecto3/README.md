
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

3. read_diabetes_tables: lee los datos por batch, genera tres tablas: train, validation y test (batch de 15000 registros)

4. diabetes_data_pipeline: limpieza de datos, procesamiento y almacenamiento de data limpia

