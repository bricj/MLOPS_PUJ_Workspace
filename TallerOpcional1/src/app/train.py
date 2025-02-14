import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib
from sklearn import linear_model
from sklearn.metrics import classification_report

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn


def load_and_clean(path,filename,feature_selection):
    
    df_lter = pd.read_csv(path + filename)
    df_lter_sample = df_lter.copy()
    df_lter_sample = df_lter_sample[feature_selection]
    df_lter_sample = df_lter_sample.dropna()
    try:
        df_lter_sample = df_lter_sample[df_lter_sample['Sex'] != '.']
    except ValueError:
        None
    print("No hay valores perdidos" if df_lter_sample.isna().sum().sum() == 0 else "Existe valores perdidos")
    
    return df_lter_sample

def transform_variables(df_lter_sample,variables_categoricas,variables_continuas):

    # Label Encoder

    le = LabelEncoder()
    for variable in variables_categoricas:
        df_lter_sample[variable] = le.fit_transform(df_lter_sample[variable])
    
    # Scale continuous variables

    scaler = MinMaxScaler()
    df_lter_sample[variables_continuas] = scaler.fit_transform(df_lter_sample[variables_continuas])
    
    return df_lter_sample

def train_model(data_path,size_filename,features,variables_categoricas,variables_continuas,data_output):
    # Load and Clean
    df = load_and_clean(data_path,size_filename,features)
    # Transform
    df = transform_variables(df,variables_categoricas,variables_continuas)
    # Train Test Split
    
    y = df[['Species']]
    X = df[['Island', 'Culmen Length (mm)', 'Culmen Depth (mm)',
       'Flipper Length (mm)', 'Body Mass (g)', 'Sex', 'Delta 15 N (o/oo)',
       'Delta 13 C (o/oo)']]

    X_train, X_test,y_train, y_test = train_test_split(X,y , 
                                   random_state=50,  
                                   test_size=0.30) 
    # Train Model
    
    model = linear_model.LogisticRegression(multi_class='ovr', solver='liblinear')
    model.fit(X_train, y_train)
    
    joblib.dump(model, data_output + "model_logreg.pkl")
    logreg_model = joblib.load(data_output + "model_logreg.pkl")
    
    y_pred = logreg_model.predict(X_test)
 
    target_names = ['Adelie', 'Gentoo', 'Chinstrap']

    print(classification_report(y_test, y_pred, target_names=target_names))
    print('-------------------------')
    print('Entrenamiento de modelo finalizado')
    
    return None

if __name__ == "__main__":
    
    # Parametros
    size_filename = "penguins_lter.csv"
    
    data_path = "/home/bric/Documents/MLOPS/MLOPS_PUJ_Workspace/Taller1/data/"
    data_output = "/home/bric/Documents/MLOPS/MLOPS_PUJ_Workspace/Taller1/src/"
    
    features = ['Species','Island','Culmen Length (mm)','Culmen Depth (mm)',
                'Flipper Length (mm)','Body Mass (g)','Sex','Delta 15 N (o/oo)','Delta 13 C (o/oo)']
    
    variables_continuas = ['Culmen Length (mm)',
       'Culmen Depth (mm)', 'Flipper Length (mm)', 'Body Mass (g)',
       'Delta 15 N (o/oo)', 'Delta 13 C (o/oo)']
    variables_categoricas = ['Species', 'Island', 'Sex']
   
    train_model(data_path,size_filename,features,variables_categoricas,variables_continuas,data_output)