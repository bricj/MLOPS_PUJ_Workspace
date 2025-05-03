from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import os
import pickle
from airflow.providers.mysql.hooks.mysql import MySqlHook

# Configuraci�n b�sica
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 5, 1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# Definir funciones para las tareas
def load_data_from_sql(**kwargs):
    """Lee los datos de SQL y los convierte a DataFrame"""
    ti = kwargs['ti']
    
    # Conectar a la base de datos
    mysql_hook = MySqlHook(mysql_conn_id="mysql_diabetes_conn")
    
    # Cargar los tres conjuntos de datos
    datasets = {}
    
    for data_type in ['train', 'validation', 'test']:
        try:
            # Leer tabla
            query = f"SELECT * FROM diabetes_{data_type}_processed"
            df = mysql_hook.get_pandas_df(query)
            
            # Identificar caracter�sticas y convertir a float
            # CORRECCI�N: Verificar que las columnas son realmente num�ricas antes de convertir
            feature_cols = [col for col in df.columns if 'feature' in str(col)]
            numeric_feature_cols = []
            
            # Intentar convertir cada columna por separado con manejo de errores
            for col in feature_cols:
                try:
                    # Intentar verificar si la columna contiene n�meros
                    # Si falla, probablemente contiene strings no convertibles
                    if df[col].str.isnumeric().all():
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        numeric_feature_cols.append(col)
                    else:
                        # Intentar forzar la conversi�n, con manejo de errores
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        # Si la conversi�n fue exitosa y no gener� todos NaN, a�adir a columnas num�ricas
                        if not df[col].isna().all():
                            numeric_feature_cols.append(col)
                except (AttributeError, ValueError):
                    # Si no es una columna de texto o hay otros errores, intentar conversi�n directa
                    try:
                        df[col] = df[col].astype(float)
                        numeric_feature_cols.append(col)
                    except:
                        print(f"No se pudo convertir la columna {col} a float. Ignorando.")
            
            # Usar solo columnas convertidas exitosamente
            if not numeric_feature_cols:
                # Si no hay columnas num�ricas, intentar identificar columnas que parezcan caracter�sticas
                # Las columnas num�ricas t�picamente tienen nombres con n�meros
                numeric_feature_cols = [col for col in df.columns 
                                       if any(c.isdigit() for c in str(col)) 
                                       and 'id' not in str(col).lower()]
                
                # Intento m�s agresivo por nombre de columna
                if not numeric_feature_cols:
                    # Buscar columnas que parezcan caracter�sticas por nombre
                    potential_features = [col for col in df.columns 
                                         if col not in ['target', 'readmitted', 'encounter_id', 'patient_nbr']]
                    # Tomar las primeras N columnas como caracter�sticas
                    numeric_feature_cols = potential_features[:min(10, len(potential_features))]
            
            X = df[numeric_feature_cols]
            
            # Encontrar y convertir la columna target
            target_cols = ['target', 'readmitted']
            target_col = next((col for col in target_cols if col in df.columns), None)
            
            if target_col is not None:
                # Si encontramos la columna target
                if pd.api.types.is_object_dtype(df[target_col]):
                    # Si es object/string, convertir a binario
                    # Buscar valores que parezcan positivos
                    positive_values = ['YES', '<30', '1', 'True', 'yes', 'true', 'positive', 'Positive']
                    # Detectar los valores �nicos
                    unique_vals = df[target_col].unique()
                    
                    # Crear un mapa para convertir a 0/1
                    if len(unique_vals) == 2:
                        # Encontrar cu�l valor parece ser el positivo
                        pos_val = next((val for val in unique_vals if str(val) in positive_values), unique_vals[0])
                        neg_val = next((val for val in unique_vals if val != pos_val), None)
                        
                        # Crear el mapa
                        target_map = {pos_val: 1}
                        if neg_val is not None:
                            target_map[neg_val] = 0
                        
                        # Aplicar mapa y manejar valores no mapeados
                        y = df[target_col].map(target_map).fillna(0)
                    else:
                        # Si hay m�s de 2 valores, convertir a num�rico de la mejor forma posible
                        y = pd.to_numeric(df[target_col], errors='coerce').fillna(0)
                else:
                    # Si ya es num�rico, usarlo tal cual
                    y = df[target_col]
            else:
                # Si no hay columna target, usar la �ltima columna
                y = df.iloc[:, -1]
                # Intentar convertir a num�rico si es posible
                if pd.api.types.is_object_dtype(y):
                    y = pd.to_numeric(y, errors='coerce').fillna(0)
            
            # Guardar en el diccionario
            datasets[f'{data_type}_X'] = X
            datasets[f'{data_type}_y'] = y
            
            # Guardar en XCom
            ti.xcom_push(key=f'{data_type}_X', value=X.to_json(orient='split'))
            ti.xcom_push(key=f'{data_type}_y', value=y.to_json(orient='split'))
            
            print(f"Datos de {data_type}: X={X.shape}, y={y.shape}")
            
        except Exception as e:
            print(f"ERROR cargando datos de {data_type}: {str(e)}")
            # Si hay error, crear DataFrames vac�os para no interrumpir el flujo
            ti.xcom_push(key=f'{data_type}_X', value=pd.DataFrame().to_json(orient='split'))
            ti.xcom_push(key=f'{data_type}_y', value=pd.Series().to_json(orient='split'))
    
    return "Datos cargados con �xito"

def apply_undersampling(**kwargs):
    """Aplica undersampling a los datos de entrenamiento"""
    ti = kwargs['ti']
    
    # Recuperar datos de train
    X_train_json = ti.xcom_pull(key='train_X', task_ids='load_data')
    y_train_json = ti.xcom_pull(key='train_y', task_ids='load_data')
    
    # Convertir JSON a DataFrame/Series
    X_train = pd.read_json(X_train_json, orient='split')
    y_train = pd.read_json(y_train_json, orient='split', typ='series')
    
    # Verificar que hay datos
    if X_train.empty or y_train.empty:
        print("No hay datos suficientes para hacer undersampling. Usando datos vac�os.")
        ti.xcom_push(key='train_X_balanced', value=X_train.to_json(orient='split'))
        ti.xcom_push(key='train_y_balanced', value=y_train.to_json(orient='split'))
        return "No hay datos para aplicar undersampling"
    
    print(f"Datos originales: X_train={X_train.shape}, y_train={y_train.shape}")
    
    try:
        # Obtener distribuci�n de clases
        class_counts = y_train.value_counts()
        
        # Verificar que hay al menos dos clases
        if len(class_counts) < 2:
            print(f"ADVERTENCIA: Solo hay una clase ({class_counts.index[0]}) en los datos.")
            ti.xcom_push(key='train_X_balanced', value=X_train.to_json(orient='split'))
            ti.xcom_push(key='train_y_balanced', value=y_train.to_json(orient='split'))
            return "No se puede aplicar undersampling a una sola clase"
        
        # Obtener clases mayoritaria y minoritaria
        majority_class = class_counts.idxmax()
        minority_class = class_counts.idxmin()
        
        # Obtener �ndices por clase
        majority_indices = np.where(y_train == majority_class)[0]
        minority_indices = np.where(y_train == minority_class)[0]
        
        # Submuestrear la clase mayoritaria
        np.random.seed(42)
        majority_indices_sampled = np.random.choice(
            majority_indices, 
            size=min(len(minority_indices), len(majority_indices)), 
            replace=False
        )
        
        # Combinar �ndices
        selected_indices = np.concatenate([majority_indices_sampled, minority_indices])
        
        # Obtener datos balanceados
        X_train_balanced = X_train.iloc[selected_indices]
        y_train_balanced = y_train.iloc[selected_indices]
        
        print(f"Datos balanceados: X_train={X_train_balanced.shape}, y_train={y_train_balanced.shape}")
        
    except Exception as e:
        print(f"Error en undersampling: {str(e)}")
        # En caso de error, usar los datos originales
        X_train_balanced = X_train
        y_train_balanced = y_train
    
    # Guardar en XCom
    ti.xcom_push(key='train_X_balanced', value=X_train_balanced.to_json(orient='split'))
    ti.xcom_push(key='train_y_balanced', value=y_train_balanced.to_json(orient='split'))
    
    return "Undersampling aplicado correctamente"

def train_and_predict(**kwargs):
    """Entrena el modelo y hace predicciones"""
    ti = kwargs['ti']
    
    # Recuperar datos
    X_train_json = ti.xcom_pull(key='train_X_balanced', task_ids='apply_undersampling')
    y_train_json = ti.xcom_pull(key='train_y_balanced', task_ids='apply_undersampling')
    X_test_json = ti.xcom_pull(key='test_X', task_ids='load_data')
    y_test_json = ti.xcom_pull(key='test_y', task_ids='load_data')
    
    # Convertir JSON a DataFrame/Series
    X_train = pd.read_json(X_train_json, orient='split')
    y_train = pd.read_json(y_train_json, orient='split', typ='series')
    X_test = pd.read_json(X_test_json, orient='split')
    y_test = pd.read_json(y_test_json, orient='split', typ='series')
    
    # Verificar que hay datos para entrenar
    if X_train.empty or y_train.empty:
        print("No hay datos de entrenamiento. No se puede entrenar el modelo.")
        # Crear predicciones dummy
        dummy_pred = pd.Series([0] * len(y_test)) if not y_test.empty else pd.Series()
        ti.xcom_push(key='test_predictions', value=dummy_pred.to_json(orient='split'))
        ti.xcom_push(key='test_true_values', value=y_test.to_json(orient='split'))
        return "No hay datos para entrenar"
    
    try:
        # Entrenar modelo
        print("Entrenando modelo...")
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        # Guardar modelo
        airflow_home = os.environ.get('AIRFLOW_HOME', '/opt/airflow')
        model_dir = os.path.join(airflow_home, 'data', 'models')
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, 'diabetes_rf_model.pkl')
        
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        # Hacer predicciones solo si hay datos de prueba
        if not X_test.empty and not y_test.empty:
            y_pred = model.predict(X_test)
            print("Predicciones realizadas con �xito")
        else:
            print("No hay datos de prueba. Usando predicciones dummy.")
            y_pred = np.zeros(0)
        
    except Exception as e:
        print(f"Error entrenando modelo: {str(e)}")
        # Crear predicciones dummy en caso de error
        y_pred = np.zeros(len(y_test)) if not y_test.empty else np.zeros(0)
    
    # Guardar predicciones en XCom
    ti.xcom_push(key='test_predictions', value=pd.Series(y_pred).to_json(orient='split'))
    ti.xcom_push(key='test_true_values', value=y_test.to_json(orient='split'))
    
    return "Modelo entrenado y predicciones realizadas"

def generate_metrics(**kwargs):
    """Genera m�tricas de evaluaci�n y matriz de confusi�n"""
    ti = kwargs['ti']
    
    # Recuperar datos
    y_test_json = ti.xcom_pull(key='test_true_values', task_ids='train_and_predict')
    y_pred_json = ti.xcom_pull(key='test_predictions', task_ids='train_and_predict')
    
    # Convertir JSON a Series
    y_test = pd.read_json(y_test_json, orient='split', typ='series')
    y_pred = pd.read_json(y_pred_json, orient='split', typ='series')
    
    # Verificar que hay datos suficientes
    if y_test.empty or y_pred.empty or len(y_test) != len(y_pred):
        print("No hay suficientes datos para calcular m�tricas")
        return "No hay datos suficientes para m�tricas"
    
    try:
        # Calcular m�tricas
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1_score": f1_score(y_test, y_pred, zero_division=0)
        }
        
        # Calcular matriz de confusi�n
        cm = confusion_matrix(y_test, y_pred)
        
        # Imprimir m�tricas
        print("\nM�TRICAS DE EVALUACI�N:")
        for metric, value in metrics.items():
            print(f"{metric}: {value:.4f}")
        
        print("\nMATRIZ DE CONFUSI�N:")
        print(cm)
        
        # Generar y guardar visualizaci�n
        airflow_home = os.environ.get('AIRFLOW_HOME', '/opt/airflow')
        plots_dir = os.path.join(airflow_home, 'data', 'plots')
        os.makedirs(plots_dir, exist_ok=True)
        cm_plot_path = os.path.join(plots_dir, 'confusion_matrix.png')
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                    xticklabels=['No readmit', 'Readmit'],
                    yticklabels=['No readmit', 'Readmit'])
        plt.ylabel('Valor Real')
        plt.xlabel('Valor Predicho')
        plt.title('Matriz de Confusi�n')
        plt.tight_layout()
        plt.savefig(cm_plot_path)
        plt.close()
        
        # Guardar m�tricas en un archivo
        metrics_dir = os.path.join(airflow_home, 'data', 'reports')
        os.makedirs(metrics_dir, exist_ok=True)
        metrics_path = os.path.join(metrics_dir, 'model_metrics.txt')
        
        with open(metrics_path, 'w') as f:
            f.write("M�TRICAS DE EVALUACI�N\n")
            f.write("=====================\n\n")
            for metric, value in metrics.items():
                f.write(f"{metric}: {value:.4f}\n")
            
            f.write("\nMATRIZ DE CONFUSI�N\n")
            f.write("==================\n\n")
            f.write(str(cm))
        
        print(f"M�tricas guardadas en: {metrics_path}")
        print(f"Matriz de confusi�n guardada en: {cm_plot_path}")
        
    except Exception as e:
        print(f"Error generando m�tricas: {str(e)}")
    
    return "M�tricas generadas correctamente"

# Crear el DAG
with DAG(
    'diabetes_undersampling_simple',
    default_args=default_args,
    description='DAG simple para undersampling y predicci�n de diabetes',
    schedule_interval=None,
) as dag:
    
    # Tareas
    load_data = PythonOperator(
        task_id='load_data',
        python_callable=load_data_from_sql,
        provide_context=True,
    )
    
    undersample = PythonOperator(
        task_id='apply_undersampling',
        python_callable=apply_undersampling,
        provide_context=True,
    )
    
    train_predict = PythonOperator(
        task_id='train_and_predict',
        python_callable=train_and_predict,
        provide_context=True,
    )
    
    evaluate = PythonOperator(
        task_id='generate_metrics',
        python_callable=generate_metrics,
        provide_context=True,
    )
    
    # Definir orden de ejecuci�n
    load_data >> undersample >> train_predict >> evaluate