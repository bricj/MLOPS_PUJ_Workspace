


* La base de Minio es el mismo sql utilizado en anteriores talleres, las credeniales estan en el taller 3 o 4 (readme)


* Se deben crear la conexiones a la base de datos de diabetes:

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

