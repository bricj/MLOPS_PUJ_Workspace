# Proyecto No. 2

A continuacion se brinda detalle del proyecto2 donde se realiza entrenamiento de modelos de ml con airflow, mlflow, minio, mysql y fastapi.

## Descripción configuración del entorno de trabajo :wrench: ##

En el presente proyecto interactúan los siguiente servicios para que a través de una API se posible consumir el modelo entrenado y realizar inferencias:

- FASTAPI (puerto 80): API donde se disponibiliza los datos, los cuales se consume por batch.
- Airflow (Puerto 8080): Orquestador que permite realizar el consumo de datos, creación de base de datos, pre-procesamiento   de datos, entrenamiento del modelo y despliegue en FASTAPI.
- Minio (UI - puerto 9001): Bucket que almacena objetos de MlFlow
- MLFlow (UI - puerto 5001): Servicio para realizar la etapa de experimentación de los modelos
- MySQL(Puerto 3306): Servicio donde se almacena la metada del modelo
- FASTAPI (Puerto 8989): API donde se disponibiliza el modelo entrenado para inferencia
- Los servicios se encuentran en contenedores de dockers, los cuales están conectados a través de redes de docker. La         herramienta de docker compose permite la integración de los servicios. Importante validar con cual nombre se crea la red de docker y de ser necesario, parametrizarla en el docker compose:

- Validar nombre de la red: docker network ls
  
- Así se registra la red de docker en docker compose, en cada contenedor se indica: "networks:proyecto2_airflow_network"
  
  networks:
  proyecto2_airflow_network:
    driver: "bridge"

  En este caso, la red se llama: "proyecto2_airflow_network" con el método bridge

  Disclaimer:
  SOLO POR SI ES NECESARIO PARA CONECTAR EL SERVICIO DEL PROFE CON EL DOCKER DE AIRFLOW 
  ``` docker network create group2_network```

## Ejecución de los servicios mediante Docker Compose: ##

1. **Clone el repositorio de GitHub en la máquina donde ejecutará el contenedor**

2. **Levantar el contenedor de Docker:**

- Una vez clonado el repositorio, identifique la carpeta de Proyecto2

- Antes de iniciar la ejecución, ir a la ruta "MLOPS_PUJ_WORKSPACE/Proyecto2/mlflow/mlflow_service.service" y validar que el "Working Directory" coincida con el path de su máquina. Por otro lado, validar que en environment se haga referencia al host de Minio (9000) y en la ejecución al host de MySQL (3306).

- En el Docker Compose se encuentran parametrizados los host, no obstante, se recomienda validar que coincidan con los mencionados en la anterior sección.

- Ubíquese en la ruta "MLOPS_PUJ_WORKSPACE/Proyecto2/" y ejecute "docker compose up --build". La anterior instrucción construirá el docker compose y activará los servicios mencionados en la anterior sección (mientras se levantan los servicios puede buscar un café o snack).

- Para iniciar con la ejecución, siga los siguiente pasos:

- Cerciorarse que los servicios están disponibles en los host indicados en la anterior sección. El host estándar es: "", para FASTAPI, adicione al final "/docs".
  
- Acceda a Minio ``` http://localhost:9001``` , las credenciales son:
  
    - usuario: admin
    - contraseña: supersecret
      
  En Minio se debe crear un bucket de S3, se recomienda crearlo con el nombre **mlflows3**. Si se cambia el nombre del contenedor, considerar ir al docker compose en la carpeta "Proyecto2" y cambiar las partes donde se haga referencia al contenedor "mlflows3" por el nuevo nombre del contenedor. En **mlflows3** se almacenarán los artefactos que se creen en *MLFlow*. Asegurese de activar todos los interruptores al configurar el bucket (Otorgar permisos).

- Acceda a MlFlow ``` http://localhost:5001``` para garantizar que el servicio funciona.
       
- Acceda a la interfaz de airflow ``` http://localhost:8080```, las credenciales son:
  
    - usuario: airflow
    - contraseña: airflow
      
  Una vez haya accedido, ubicarse en la sección de DAGs, donde encontrará las etapas que articula airflow. Validar que     todos se encuentren activos.

Ejecute el DAG Orquestador (El DAG está configurado para que se ejecute a diario, por ello, una vez se abra airflow, iniciará una única ejecución en el día) , el cual activará los DAGs en la secuencia establecida:

    - a) Limpiar la base de datos
    
    - b) Consumir los datos por batch de FASTAPI, se ha parametrizado para que realicen 10 consultas, cada una por minuto.
    
    - c) Preprocesamiento de los datos
    
    - d) Entrenamiento de los modelos con MlFlow
    
    - e) API de inferencia que consume el modelo cargado en produción        

Mientras se ejecutan los DAGs, le brindamos algo de detalle. Más adelante, podrá continuar con el proceso de inferencia.

3. **Detalle captura de información y entrenamiento del modelo:computer:**

**DAG fetch_and_store_data.py & preprocess_data.py**

-  El plantemiento de la obtención de datos busca establecer un problema real y es que no siempre es posible acceder a la información en su totalidad por limitaciones de cómputo, por consiguiente, a través de airflow, se ha creado un proceso iterativo para conectarse a endpoint cada minuto, aspecto que está alineado con el cambio de batch por minuto. También es posible activar con ejecución por minuto.
   
- Creación de tablas dentro de la base de datos *mysql*
  
- Carga de datos crudos a *mysql*
  
- Preprocesamiento de datos

**DAG train.py**

- Entrenamiento de modelos utilizando MLFlow:
  
  - Configuración de variables de entorno que apuntan al servicio de *MLFlow*. El servicio de *MLFlow* se conecta con un bucket de almacenamiento de minio, por ello, es necesario ingresar las credenciales de acceso mencionadas en el numeral 1, al igual que se debe ingresar la IP de la maquina donde se esta realizando la ejecucion.

  Considerar las siguiente variables que se encuentran en el docker compose (contenedor de MlFlow). Se establece la conexión entre Minio (acceso) y MlFlow. Por último, el comando establece la conexión con MySQL, donde se guarda la metadata.

      MLFLOW_S3_ENDPOINT_URL: http://minio:9000
  
      AWS_ACCESS_KEY_ID: admin
  
      AWS_SECRET_ACCESS_KEY: supersecret
  
      MLFLOW_TRACKING_URI: http://mlflow:5000
  
      command: mlflow server --backend-store-uri mysql+pymysql://airflow:airflow@mysql:3306/mlflow --default-artifact-  root s3://mlflows3/artifacts --host 0.0.0.0 --port 5000 --serve-artifacts

  - En la ejecucion de DAG, se realiza el entrenamiento del modelo y se guardan los artefactos de mlflow en minio. En el DAG se han indicado los host y credenciales para garantizar el acceso y conectividad que permiten las redes de docker. No obstante, se recomienda validar que coincidan según el servicio. Importante considerar que el modelo se registra bajo el nombre *svm-model*.
  
Dicho nombre es relevante para realizar la conexion con fastapi, tener en cuenta si se realiza el cambio del mismo. Los siguientes parámetros permite que el experimento se almacene de manera correcta en MlFlow, al igual que se guarden los experimentos.

  mlflow.set_tracking_uri("http://mlflow:5000")
  
  mlflow.set_experiment("mlflow_tracking_examples_4")
 
Mediante la siguiente instrucción, se lleva el mejor modelo a ambiente de producción, el cual será consumido por la API de inferencia:

 # Transicionar a producción
        client.transition_model_version_stage(
            name=model_name,
            version=model_version,
            stage="Production"
        )

4. **Inferencia del modelo con fastapi :computer:**

- Acceda a FASTAPI ``` http://localhost:8989/docs```

  - La inferencia en fastapi contempla dos secciones:

   - La primera seccion expone los nombres de los modelos, el estado de despliegue en el que se encuentren (produccion, staging o sin estado). 

   - En la segunda seccion se realiza la inferencia, donde se ingresa el nombre del modelo y la version a ejecutar. Una vez ingresada la informacion mencionada, se ingresan los valores para realizar la estimacion.

   - La inferencia de fastapi establece conexion con el modulo model registry de mlflow, el cual no requiere de la implementacion de volumenes para la transmision de informacion.


4. **Conclusiones:**

   El proyecto desarrollo expone un escenario controlado para acceder a datos mediante batch, lo cual es una situación cotidiana en el día a día porque la ingesta de datos no siempre puede realizarse en "una corrida" por el volumen de datos o limitaciones de computo.

 La integración de airflow y mlflow permite establecer un flujo de proceso "continuo" para experimentar con cierta frecuencia, que sumado al consumo de datos por batch, se emula la ingesta de nuevos datos, hecho que está asociado a la realidad.

Cabe resaltar que la integración de airflow y mlflow demanda atención en la selección de las versiones de las dependencias, por ello, es importante tener cuidado en la construcción de los servicios.

Las redes de docker permiten la conectividad de los contenedores sin que ello implique un traspaso de información como se hace con los volúmenes. Lo anterior permite establecer los servicios bajo un "mismo entorno".
