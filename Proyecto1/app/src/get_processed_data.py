import os
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.feature_selection import chi2
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import OneHotEncoder
import seaborn as sns
from ml_metadata import metadata_store
from ml_metadata.proto import metadata_store_pb2

quantitative_variables = ['Elevation', 'Aspect', 'Slope', 'Horizontal_Distance_To_Hydrology',
       'Vertical_Distance_To_Hydrology', 'Horizontal_Distance_To_Roadways',
       'Hillshade_9am', 'Hillshade_Noon', 'Hillshade_3pm',
       'Horizontal_Distance_To_Fire_Points']

categorical_variables = ['Wilderness_Area', 'Soil_Type']

target_value = ['Cover_Type']

def get_data():

    ## download the dataset
    # Directory of the raw data files
    _data_root = './data/covertype'
    # Path to the raw training data
    _data_filepath = os.path.join(_data_root, 'covertype_train.csv')
    # Download data
    os.makedirs(_data_root, exist_ok=True)
    if not os.path.isfile(_data_filepath):
     #https://archive.ics.uci.edu/ml/machine-learning-databases/covtype/
     url = 'https://docs.google.com/uc?export= \
     download&confirm={{VALUE}}&id=1lVF1BCWLH4eXXV_YOJzjR7xZjj-wAGj9'
     r = requests.get(url, allow_redirects=True, stream=True)
     open(_data_filepath, 'wb').write(r.content)
    
    # Read the CSV file into a DataFrame
    if os.path.exists(_data_filepath):
        df = pd.read_csv(_data_filepath)
        print("Dataframe was loaded")  # Display the first few rows
    else:
        df = pd.read_csv()
        print(f"File not found: {_data_filepath}")

    return df

def numerical_feature_selection(df,num_variables,target_value,k_num=4):
    """
    Function:
    * Se realiza Feature Selection para variables numericas mediante analisis de ANOVA
    
    Inputs
    * df: dataframe objeto de analisis
    * num_variables: nombre de variables numericas
    * target_value: nombre de variable objetivo en el modelo de aprendizaje de maquina
    * k_num: cantidad de variables a seleccionar

    Outputs:
    * selected_num_features: variables numericas seleccionadas

    """   
    scaler = MinMaxScaler()
    X_encoded_num = scaler.fit_transform(df[num_variables])
    df_X_encoded_num = pd.DataFrame(X_encoded_num, 
                              columns=scaler.get_feature_names_out(num_variables))
    
    selector_num = SelectKBest(score_func=f_classif, k=k_num)
    selector_num.fit(X_encoded_num, df[target_value] )
    num_columns = df_X_encoded_num.columns
    selected_num_features = list(num_columns[selector_num.get_support()])
    
    num_analysis_result = pd.DataFrame(zip(num_columns,selector_num.get_support()),columns=["Columns","Retain"])
    print("---------------------------" )
    print("Selected Numerical Values" )
    print(num_analysis_result)
    
    return df_X_encoded_num[selected_num_features]

def categorical_feature_selection(df,cat_variables,target_value,k_cat=9):
    """
    Function:
    * Se realiza Feature Selection para variables numericas mediante analisis de Chi2
    
    Inputs
    * df: dataframe objeto de analisis
    * num_variables: nombre de variables categoricas
    * target_value: nombre de variable objetivo en el modelo de aprendizaje de maquina
    * k_num: cantidad de variables a seleccionar

    Outputs:
    * selected_num_features: variables categoricas seleccionadas

    """   
    encoder = OneHotEncoder(sparse_output=False)
    X_encoded_cat = encoder.fit_transform(df[cat_variables])
    df_X_encoded_cat = pd.DataFrame(X_encoded_cat, 
                          columns=encoder.get_feature_names_out(cat_variables))

    selector_cat = SelectKBest(score_func=chi2, k=k_cat)
    selector_cat.fit(X_encoded_cat, df[target_value] )
    cat_columns = df_X_encoded_cat.columns
    selected_cat_features = list(cat_columns[selector_cat.get_support()])
    
    cat_analysis_result = pd.DataFrame(zip(cat_columns,selector_cat.get_support()),columns=["Columns","Retain"])
    print("---------------------------" )
    print("Selected Categorical Values" )
    print(cat_analysis_result)
    
    return df_X_encoded_cat[selected_cat_features]

def get_artifacts_details(store, type_name):
    """
    Function:
    * Obtiene el detalle de los artefactos dentro de los metadatos.
    
    Inputs
    * store: almacenamiento de metadatos.
    * type_name: nombre del tipo de metadato a consultar.

    Outputs:
    * df: dataframe con la información del artefacto solicitado.

    """ 
    artifacts = store.get_artifacts_by_type(type_name)
    data = []
    
    for artifact in artifacts:
        data.append({
            'Artifact ID': artifact.id,
            'Type': type_name,
            'URI': artifact.uri
        })

    df = pd.DataFrame(data)
    return df

