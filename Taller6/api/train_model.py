import pandas as pd
import joblib
import os
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.model_selection import GridSearchCV
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.svm import SVC

# Configuración y rutas
print("Iniciando entrenamiento del modelo...")

# Usar rutas relativas para mayor compatibilidad
# Rutas correctas para ejecutar desde /api
DATA_PATH = "./data/covertype.csv"  # Se resuelve a /api/data/covertype.csv
OUTPUT_DIR = "./model"  # Se resuelve a /api/model

# Asegurar que el directorio de salida exista
os.makedirs(OUTPUT_DIR, exist_ok=True)

try:
    print(f"Intentando cargar datos desde: {DATA_PATH}")
    
    # Verificar si el archivo existe
    if not os.path.exists(DATA_PATH):
        print(f"¡ERROR! El archivo {DATA_PATH} no existe")
        print("Directorio actual:", os.getcwd())
        print("Contenido del directorio:")
        print(os.listdir('.'))
        
        # Verificar si existe el directorio data
        if os.path.exists("data"):
            print("Contenido del directorio data:")
            print(os.listdir("data"))
        raise FileNotFoundError(f"No se encontró el archivo {DATA_PATH}")
    
    # Cargar un subconjunto pequeño de datos para acelerar el entrenamiento
    # Leer solo las primeras 5000 filas
    df = pd.read_csv(DATA_PATH, nrows=5000)
    print(f"Datos cargados: {df.shape[0]} filas, {df.shape[1]} columnas")
    
    # Corregir las listas
    variables_categoricas = ['Wilderness_Area', 'Soil_Type', 'Cover_Type']
    variables_continuas = ['Elevation', 'Aspect', 'Slope', 'Horizontal_Distance_To_Hydrology',
                          'Vertical_Distance_To_Hydrology', 'Horizontal_Distance_To_Roadways',
                          'Hillshade_9am', 'Hillshade_Noon', 'Hillshade_3pm',
                          'Horizontal_Distance_To_Fire_Points']
    
    # Preprocesamiento básico
    print("Aplicando preprocesamiento...")
    
    # Codificación de variables categóricas
    for cat_var in variables_categoricas:
        if cat_var != 'Cover_Type':  # No transformar la variable objetivo
            le = LabelEncoder()
            df[cat_var] = le.fit_transform(df[cat_var])
    
    # Escalado de variables continuas
    for num_var in variables_continuas:
        scaler = MinMaxScaler()
        df[num_var] = scaler.fit_transform(df[[num_var]])
    
    # Preparar datos para entrenamiento
    print("Preparando datos para entrenamiento...")
    y = df['Cover_Type']
    X = df[['Elevation', 'Aspect', 'Slope', 'Horizontal_Distance_To_Hydrology',
           'Vertical_Distance_To_Hydrology', 'Horizontal_Distance_To_Roadways',
           'Hillshade_9am', 'Hillshade_Noon', 'Hillshade_3pm',
           'Horizontal_Distance_To_Fire_Points', 'Wilderness_Area',
           'Soil_Type']]
    
    # Dividir en entrenamiento y prueba
    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42, test_size=0.2)
    print(f"Datos de entrenamiento: {X_train.shape[0]} muestras")
    print(f"Datos de prueba: {X_test.shape[0]} muestras")
    
    # Entrenar un modelo SVM sencillo (parámetros reducidos para acelerar)
    print("Entrenando modelo SVM...")
    svm = SVC(kernel='linear', probability=True)
    
    # Grid search muy simple (un solo parámetro, una sola validación)
    params = {'C': [1.0]}
    grid_search = GridSearchCV(svm, params, cv=2, scoring='accuracy', n_jobs=-1)
    grid_search.fit(X_train, y_train)
    
    # Evaluar modelo
    accuracy = grid_search.score(X_test, y_test)
    print(f"Precisión del modelo: {accuracy:.4f}")
    
    # Guardar modelo
    model_path = os.path.join(OUTPUT_DIR, "model_svm.pkl")
    print(f"Guardando modelo en {model_path}")
    joblib.dump(grid_search, model_path)
    
    print("Entrenamiento completado exitosamente")
    
except Exception as e:
    print(f"Error durante el entrenamiento: {str(e)}")
    raise

# import pandas as pd
# import joblib
# from sklearn.model_selection import train_test_split
# from sklearn.model_selection import GridSearchCV
# from sklearn.preprocessing import LabelEncoder, MinMaxScaler
# from sklearn.svm import SVC


# DATA_PATH = "./api/data/covertype.csv" 
# DATA_OUTPUT = "./api/app/"

# df = pd.read_csv(DATA_PATH)

# variables_categoricas =  ['Wilderness_Area','Soil_Type',
#        'Cover_Type']
    
# variables_continuas = ['Elevation', 'Aspect', 'Slope', 'Horizontal_Distance_To_Hydrology',
#     'Vertical_Distance_To_Hydrology', 'Horizontal_Distance_To_Roadways',
#     'Hillshade_9am', 'Hillshade_Noon', 'Hillshade_3pm',
#     'Horizontal_Distance_To_Fire_Points', 'Wilderness_Area']

# le = LabelEncoder()
# for cat_var in variables_categoricas:
#     df[cat_var] = le.fit_transform(df[cat_var])

# scaler = MinMaxScaler()
# for num_var in variables_continuas:
#     df[num_var] = scaler.fit_transform(df[num_var])


# # Particion datos de entrenamiento y evaluacion
# y = df['Cover_Type']
# X = df[['Elevation', 'Aspect', 'Slope', 'Horizontal_Distance_To_Hydrology',
#     'Vertical_Distance_To_Hydrology', 'Horizontal_Distance_To_Roadways',
#     'Hillshade_9am', 'Hillshade_Noon', 'Hillshade_3pm',
#     'Horizontal_Distance_To_Fire_Points', 'Wilderness_Area','Wilderness_Area',
#     'Soil_Type']]

# # Dividir entre entrenamiento y validacion
# X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=50, test_size=0.30)

# # inicializar svm
# svm = SVC()

# params = {
#         'C': [0.1, 1],
#         'gamma': ['scale', 0.1]}

# # buscar hiperparametros mas optimos
# grid_search = GridSearchCV(svm, params, cv=5, scoring='accuracy', n_jobs=-1)
# grid_search.fit(X_train, y_train)

# joblib.dump(grid_search, DATA_OUTPUT + "model_svm.pkl")
