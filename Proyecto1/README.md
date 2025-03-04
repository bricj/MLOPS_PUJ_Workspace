## Descargar el repositorio :computer: #
para descargar el repositorio puedes hacer uso del siguiente comando
```bash
git clone https://github.com/bricj/MLOPS_PUJ_Workspace.git 
```

Luego, debes ubicarte en la carpeta del repositorio y navegar hacia la carpeta **Proyecto1**.
Una vez en la carpeta vas a crear la imagen Docker y su contenedor asociado  escribiendo en la terminal
```bash
docker-compose  up --build
```
Una vez que se ha creado adecuadamente la imagen Docker y el contenedor ya se encuentre en funcionamiento, tendrás disponible en la terminal 
un enlace muy similar a este: ```http://127.0.0.1:8888/lab?token=access-token```. Cópialo y pégalo en tu navegador para acceder al entorno de jupyter lab.

__IMPORTANTE__: en caso de que se encuentre, la carpeta app/src/data/covertype/.ipynb_checkpoints debe ser borrada antes de montar el contenedor

# Ambiente de desarrollo ML

## Contenedor

El ambiente se encuentra soportado sobre un contenedor docker. Este contenedor docker posee las siguientes características.

 - La imagen es python:3.10
 - El entorno virtual es manejado con uv. En la construcción de la imagen los archivos pyproject.toml y uv.lock son copiados a la carpeta src
 - Dentro de la carpeta src tambien se encuentra la carpeta app la cual es un volumen que contiene los notebook, los datos y todos los artefactos TFX
 - Actua sobre el puerto 8888, el cual se encuentra conectado al puerto 8888 del computador host
 - AL ser montado, se ejecuta un comando que corre jupyter lab

## visualización y ejecución de los Notebooks :rocket: #

Una vez estés dentro del entorno de jupyter Lab navega dentro de la carpera **src**, allí encontrarás los notebooks pre-process_data.ipynb y pipeline.ipynb. También encontrarás el código de python get_processed_data.py.

### get_processed_data.py

Este módulo contiene las siguientes funciones:

- **get_data:** Descarga los datos que se usan durante el ejercicio planteado. Retorna un datastream con los datos para trabajar.
- **numerical_feature_selection:** Se realiza Feature Selection para variables numericas mediante analisis de ANOVA. Retorna las variables numéricas seleccionadas.
- **categorical_feature_selection:** Se realiza Feature Selection para variables categóricas binarizadas mediante analisis de Chi2. Retorna las variables categóricas seleccionadas.
- **get_artifacts_details:** Obtiene el detalle de los artefactos dentro de los metadatos. Entrega un dataframe con la información del artefacto solicitado.

### pre-process_data.ipynb

Este notebook se encarga de la exploración y el preprocesamiento del conjunto de datos utilizado para el proyecto 1. Se compone de las siguientes secciones:

- Load data: Carga de la información.
- Feature Selection
  - Data exploration: Para determinar que variables son categóricas y que variables son numéricas.
  - Feature analysis
    - Quantitative analysis: Se calcula la correlación entre variables, se observan valores promedio, mínimos y máximos. Luego se normalizan las variables utilizando _Min Max Scaler_ y finalmente se seleccionan un subconjunto de 4 variables.
    - Categorial analysis: Se observa el balance de las clases categóricas. Luego, se usa _One Hot Encoding_ para transformar las variables en columnas dummy. Finalmente, se seleccionan las 9 variables dummy más significativas.
  - Feature selection function: Se encarga de crear el conjunto de datos que será utilizado durante el desarrollo del proyecto.

### pipeline-metadata.ipynb

Este notebook desarrolla los puntos propuestos por el proyecto para las secciones Pipeline y Metadata:

- Pipeline


  - Configurar el contexto interactivo
  - Genera ejemplos con los cuales trabajar
  - A partir de los ejemplos, genera estadísticas
  - Utilizando las estadísticas, crea un esquema de los datos
  - El esquema es curado insertando dominios para algunas características
  - Se crean dos entornos de esquema, uno para entrenamiento, y otro para inferencias, ya que uno tiene la etiqueta y el otro no
  - Las modificaciones del esquema son almacenadas en un nuevo artefacto de esquema
  - Se buscan anomalías entre el ejemplo y el nuevo esquema
  - Se crea un artefacto de Transformar para aplicar el esquema y las transformaciones al ejemplo, esto es necesario ya que se presentaron anomalias por inconsistencias de tipo de datos entre el ejemplo y el esquema curado

    
- Metadatos
  - Acceso a artefactos almacenados
  - Seguimiento de artefactos
  - Obtener artefactos principales
 
### processing_for_tfx.py

El artefacto Transform requiere importar, desde un modulo, la función que contiene las transformaciones a los datos. Este archivo Python contiene dicha función.
