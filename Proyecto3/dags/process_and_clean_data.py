"""
DAG para leer las tablas de datos de diabetes (train, validation, test),
preprocesarlas con un pipeline y guardar los resultados en nuevas tablas.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
import pickle
import os
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder

# Configuraci�n de logging
logger = logging.getLogger(__name__)

# Argumentos por defecto para el DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 5, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# Funci�n para leer datos de una tabla espec�fica
def read_diabetes_table(table_type, **kwargs):
    """
    Lee una tabla de diabetes y registra informaci�n sobre filas y columnas.
    
    Args:
        table_type: Tipo de tabla a leer ('train', 'validation' o 'test')
        
    Returns:
        DataFrame con los datos le�dos (tambi�n guardado en XCom)
    """
    table_name = f"diabetes_{table_type}"
    logger.info(f"Iniciando lectura de tabla {table_name}...")
    
    try:
        # Conectar a MySQL usando la conexi�n configurada en Airflow
        mysql_hook = MySqlHook(mysql_conn_id="mysql_diabetes_conn")
        
        # Leer la tabla completa en un DataFrame
        query = f"SELECT * FROM {table_name}"
        df = mysql_hook.get_pandas_df(query)
        
        # Registrar informaci�n sobre los datos le�dos
        num_rows = len(df)
        num_cols = len(df.columns)
        
        logger.info(f" Tabla {table_name} le�da exitosamente:")
        logger.info(f"   - Filas: {num_rows}")
        logger.info(f"   - Columnas: {num_cols}")
        logger.info(f"   - Nombres de columnas: {', '.join(df.columns.tolist())}")
        
        # Registrar informaci�n sobre valores nulos
        null_counts = df.isnull().sum().sum()
        logger.info(f"   - Total de valores nulos: {null_counts}")
        
        # Guardar resultados en XCom para uso posterior
        kwargs['ti'].xcom_push(key=f'{table_type}_rows', value=num_rows)
        kwargs['ti'].xcom_push(key=f'{table_type}_columns', value=num_cols)
        kwargs['ti'].xcom_push(key=f'{table_type}_data', value=df.to_json(orient='split'))
        
        # Retornar el DataFrame
        return df
    
    except Exception as e:
        logger.error(f" Error al leer tabla {table_name}: {str(e)}")
        raise

def level1_diag1(x):
    """
    Maps diagnosis codes to categorical levels
    
    Parameters:
    -----------
    x : int or str
        Diagnosis code
        
    Returns:
    --------
    int
        Mapped diagnosis category (0-8)
    """
    if isinstance(x, (int, float)) and not np.isnan(x):
        x = int(x)
        if (x >= 390 and x < 460) or (np.floor(x) == 785):
            return 1
        elif (x >= 460 and x < 520) or (np.floor(x) == 786):
            return 2
        elif (x >= 520 and x < 580) or (np.floor(x) == 787):
            return 3
        elif (np.floor(x) == 250):
            return 4
        elif (x >= 800 and x < 1000):
            return 5
        elif (x >= 710 and x < 740):
            return 6
        elif (x >= 580 and x < 630) or (np.floor(x) == 788):
            return 7
        elif (x >= 140 and x < 240):
            return 8
        else:
            return 0
    else:
        return 0

def preprocess_diabetes_data(df):
    """
    Preprocesses the diabetes dataset by handling categorical and numerical variables,
    creating derived features, and preparing the target variable.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        The diabetes dataframe to preprocess
        
    Returns:
    --------
    X : pandas.DataFrame
        Preprocessed features dataframe
    y : pandas.Series
        Target variable (readmitted)
    """
    # Define column categories
    ids_cols = ['encounter_id', 'patient_nbr']
    
    categorical_cols = ['race', 'gender', 'age', 'admission_type_id', 'discharge_disposition_id', 
                       'admission_source_id', 'payer_code', 'medical_specialty',
                       'metformin', 'repaglinide', 'nateglinide', 'chlorpropamide',
                       'glimepiride', 'acetohexamide', 'glipizide', 'glyburide', 'tolbutamide',
                       'pioglitazone', 'rosiglitazone', 'acarbose', 'miglitol', 'troglitazone',
                       'tolazamide', 'examide', 'citoglipton', 'insulin',
                       'glyburide-metformin', 'glipizide-metformin',
                       'glimepiride-pioglitazone', 'metformin-rosiglitazone',
                       'metformin-pioglitazone', 'change', 'readmitted', 'diag_1', 'diag_2', 'diag_3',
                       'diabetesMed', 'max_glu_serum', 'A1Cresult']
    
    # Verificar si hay columna 'change_column' en lugar de 'change'
    if 'change_column' in df.columns and 'change' not in df.columns:
        # Reemplazar en la lista
        categorical_cols = [col.replace('change', 'change_column') for col in categorical_cols]
    
    numerical_cols = ['time_in_hospital', 'num_lab_procedures', 'num_procedures', 'num_medications',
                     'number_outpatient', 'number_emergency', 'number_inpatient', 'number_diagnoses']
    
    # Filtrar columnas que existen en el DataFrame
    cat_cols_exist = [col for col in categorical_cols if col in df.columns]
    num_cols_exist = [col for col in numerical_cols if col in df.columns]
    
    # Split dataframe into categorical and numerical parts
    df_diabetes_cat = df[cat_cols_exist]
    df_diabetes_num = df[num_cols_exist]
    
    # Process target variable
    y = df['readmitted'].copy()
    y = y.apply(lambda x: 'YES' if (x == '<30') else 'NO')
    
    # Process numerical variables
    df_diabetes_num['service_utilization'] = (df_diabetes_num['number_outpatient'] + 
                                             df_diabetes_num['number_emergency'] + 
                                             df_diabetes_num['number_inpatient'])
    
    # Process categorical variables - adaptamos para usar los nombres correctos de columnas
    no_representative_cat = ['repaglinide', 'nateglinide', 'chlorpropamide', 'acetohexamide', 
                            'tolbutamide', 'acarbose', 'miglitol', 'troglitazone',
                            'tolazamide', 'glyburide-metformin', 'glipizide-metformin',
                            'glimepiride-pioglitazone', 'metformin-rosiglitazone', 
                            'metformin-pioglitazone', 'payer_code', 
                            'medical_specialty', 'diag_2', 'diag_3']
    
    # Filtrar columnas no representativas que existen en el DataFrame
    no_representative_cat = [col for col in no_representative_cat if col in df_diabetes_cat.columns]
    
    df_diabetes_cat_depured = df_diabetes_cat.drop(no_representative_cat, axis=1)
    X_cat = df_diabetes_cat_depured.drop('readmitted', axis=1)
    
    # Fill missing values
    X_cat = X_cat.fillna('?')
    
    # Process diagnosis codes
    X_cat['diag_1'] = X_cat['diag_1'].apply(lambda x: level1_diag1(x))
    
    # Group admission source ID
    admission_source_mapping = {
        2: 1, 3: 1,  # Group to 1
        5: 4, 6: 4, 8: 4, 10: 4, 18: 4, 22: 4, 25: 4, 26: 4,  # Group to 4
        15: 9, 17: 9, 20: 9, 21: 9,  # Group to 9
        13: 11, 14: 11, 23: 11, 24: 11  # Group to 11
    }
    X_cat['admission_source_id'] = X_cat['admission_source_id'].replace(admission_source_mapping)
    
    # Group admission type ID
    admission_type_mapping = {
        2: 1, 7: 1, 4: 1,  # Group to Emergency (1)
        6: 5, 8: 5  # Group to Not available (5)
    }
    X_cat['admission_type_id'] = X_cat['admission_type_id'].replace(admission_type_mapping)
    
    # Group discharge disposition ID
    discharge_mapping_1 = {6: 1, 8: 1, 13: 1, 19: 1, 20: 1}  # Group to 1
    discharge_mapping_2 = {3: 2, 4: 2, 5: 2, 9: 2, 10: 2, 12: 2, 14: 2, 22: 2, 23: 2, 24: 2}  # Group to 2
    discharge_mapping_15 = {16: 15, 17: 15, 27: 15, 28: 15, 29: 15, 30: 15}  # Group to 15
    discharge_mapping_18 = {25: 18, 26: 18}  # Group to 18
    
    discharge_mapping = {**discharge_mapping_1, **discharge_mapping_2, **discharge_mapping_15, **discharge_mapping_18}
    X_cat['discharge_disposition_id'] = X_cat['discharge_disposition_id'].replace(discharge_mapping)
    
    # Combine categorical and numerical features
    X = pd.concat([X_cat, df_diabetes_num], axis=1)
    
    # Conservar los IDs para poder reconstruir el DataFrame original despu�s
    ids = df[ids_cols] if all(col in df.columns for col in ids_cols) else None
    
    return X, y, ids

def create_preprocessing_pipeline(X):
    """
    Creates a preprocessing pipeline for transforming categorical and numerical variables
    using scikit-learn's ColumnTransformer.
    
    Parameters:
    -----------
    X : pandas.DataFrame
        DataFrame containing the features to transform
    
    Returns:
    --------
    preprocessor : ColumnTransformer
        Fitted ColumnTransformer object for preprocessing the data
    X_transformed : numpy.ndarray
        Transformed feature matrix
    """
    # Define default columns
    cat_cols = ['race', 'gender', 'age', 'admission_type_id',
               'discharge_disposition_id', 'admission_source_id', 'metformin',
               'glimepiride', 'glyburide', 'pioglitazone', 'rosiglitazone', 'examide',
               'citoglipton', 'insulin', 'change', 'diag_1', 'diabetesMed',
               'max_glu_serum', 'A1Cresult']
    
    # Verificar si hay columna 'change_column' en lugar de 'change'
    if 'change_column' in X.columns and 'change' not in X.columns:
        # Reemplazar en la lista
        cat_cols = [col.replace('change', 'change_column') for col in cat_cols]
    
    num_cols = ['time_in_hospital', 'num_lab_procedures',
               'num_procedures', 'num_medications', 'number_outpatient',
               'number_emergency', 'number_inpatient', 'number_diagnoses', 
               'service_utilization']
    
    # Validate that the columns exist in the DataFrame
    missing_cat_cols = [col for col in cat_cols if col not in X.columns]
    missing_num_cols = [col for col in num_cols if col not in X.columns]
    
    if missing_cat_cols:
        logger.warning(f"Categorical columns not found in DataFrame: {missing_cat_cols}")
        # Filtrar para usar solo columnas existentes
        cat_cols = [col for col in cat_cols if col in X.columns]
    
    if missing_num_cols:
        logger.warning(f"Numerical columns not found in DataFrame: {missing_num_cols}")
        # Filtrar para usar solo columnas existentes
        num_cols = [col for col in num_cols if col in X.columns]
    
    # Pipeline for numerical columns
    numeric_pipeline = Pipeline([
        ("scaler", StandardScaler())
    ])
    
    # Pipeline for categorical columns
    categorical_pipeline = Pipeline([
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])
    
    # Create column transformer
    preprocessor = ColumnTransformer([
        ("num", numeric_pipeline, num_cols),
        ("cat", categorical_pipeline, cat_cols)
    ])
    
    # Fit and transform the data
    X_transformed = preprocessor.fit_transform(X)
    
    return preprocessor, X_transformed

def preprocess_table(table_type, **kwargs):
    """
    Preprocesa los datos de diabetes utilizando el pipeline.
    
    Args:
        table_type: Tipo de tabla a procesar ('train', 'validation' o 'test')
        
    Returns:
        None (los resultados se guardan en XCom)
    """
    ti = kwargs['ti']
    
    # Recuperar los datos de la tarea anterior
    data_json = ti.xcom_pull(key=f'{table_type}_data', task_ids=f'read_{table_type}_data')
    
    if not data_json:
        logger.error(f"✗ No se encontraron datos para la tabla {table_type}")
        raise ValueError(f"No data found for table {table_type}")
    
    # Convertir JSON a DataFrame
    df = pd.read_json(data_json, orient='split')
    
    logger.info(f"Iniciando preprocesamiento de datos {table_type}...")
    
    # Preprocesar los datos
    try:
        # Preprocesar los datos
        X, y, ids = preprocess_diabetes_data(df)
        
        # Crear el pipeline de transformación
        preprocessor, X_transformed = create_preprocessing_pipeline(X)
        
        # Directorio para almacenar el preprocessor
        airflow_home = os.environ.get('AIRFLOW_HOME', '/opt/airflow')
        model_dir = os.path.join(airflow_home, 'data', 'models')
        os.makedirs(model_dir, exist_ok=True)
        preprocessor_path = os.path.join(model_dir, 'diabetes_preprocessor.pkl')
        
        # Guardar el transformador en un archivo para train o usar el guardado para validation/test
        if table_type == 'train':
            # Serializar y guardar el preprocessor en un archivo
            with open(preprocessor_path, 'wb') as f:
                pickle.dump(preprocessor, f)
            logger.info(f"Preprocessor guardado en: {preprocessor_path}")
            
            # Guardar la ruta en XCom (esto es string, no bytes)
            kwargs['ti'].xcom_push(key='preprocessor_path', value=preprocessor_path)
        
        elif table_type in ['validation', 'test']:
            # Recuperar la ruta del preprocessor
            preprocessor_path = ti.xcom_pull(key='preprocessor_path', task_ids=f'preprocess_train_data')
            
            if not preprocessor_path or not os.path.exists(preprocessor_path):
                logger.error("✗ No se encontró el preprocessor del entrenamiento")
                raise ValueError("Preprocessor from training not found")
            
            # Cargar el preprocessor
            with open(preprocessor_path, 'rb') as f:
                preprocessor = pickle.load(f)
            
            # Transformar los datos utilizando el mismo preprocessor del entrenamiento
            X_transformed = preprocessor.transform(X)
        
        # Convertir a DataFrame para facilitar su uso
        X_transformed_df = pd.DataFrame(X_transformed)
        
        # Añadir la columna target
        processed_df = X_transformed_df.copy()
        processed_df['target'] = y.values
        
        # Si hay IDs, añadirlos al DataFrame procesado
        if ids is not None:
            for col in ids.columns:
                # Es importante asegurarse de que los valores de IDs sean correctos
                # y no nombres de columnas
                processed_df[col] = ids[col].values
        else:
            # Si no hay IDs, añadir índices como IDs
            logger.warning("No se encontraron columnas de ID en los datos originales. Generando IDs...")
            processed_df['encounter_id'] = np.arange(1, len(processed_df) + 1)
            processed_df['patient_nbr'] = np.arange(1, len(processed_df) + 1)
        
        # Guardar en XCom
        processed_json = processed_df.to_json(orient='split')
        kwargs['ti'].xcom_push(key=f'{table_type}_processed_data', value=processed_json)
        
        # Registrar información sobre los datos procesados
        logger.info(f"✓ Datos {table_type} preprocesados exitosamente:")
        logger.info(f"   - Filas: {len(processed_df)}")
        logger.info(f"   - Columnas: {len(processed_df.columns)}")
        
        return processed_df
        
    except Exception as e:
        logger.error(f"✗ Error al preprocesar datos {table_type}: {str(e)}")
        raise

# def save_processed_table(table_type, **kwargs):
#     """
#     Guarda los datos procesados en una tabla de MySQL.
    
#     Args:
#         table_type: Tipo de tabla a guardar ('train', 'validation' o 'test')
        
#     Returns:
#         None
#     """
#     ti = kwargs['ti']
    
#     # Recuperar los datos procesados de XCom
#     processed_json = ti.xcom_pull(key=f'{table_type}_processed_data', task_ids=f'preprocess_{table_type}_data')
    
#     if not processed_json:
#         logger.error(f"✗ No se encontraron datos procesados para la tabla {table_type}")
#         raise ValueError(f"No processed data found for table {table_type}")
    
#     # Convertir JSON a DataFrame
#     processed_df = pd.read_json(processed_json, orient='split')
    
#     # Nombre de la tabla de destino
#     target_table = f"diabetes_{table_type}_processed"
    
#     logger.info(f"Guardando datos procesados en tabla {target_table}...")
    
#     try:
#         # Conectar a MySQL
#         mysql_hook = MySqlHook(mysql_conn_id="mysql_diabetes_conn")
        
#         # Verificar si hay columnas 'encounter_id' y 'patient_nbr' que sean strings en lugar de enteros
#         for col in ['encounter_id', 'patient_nbr']:
#             if col in processed_df.columns and processed_df[col].dtype == 'object':
#                 # Si la columna existe y es de tipo object (string), verificar si contiene el nombre de la columna
#                 if (processed_df[col] == col).any():
#                     logger.warning(f"Columna {col} contiene su propio nombre como valor. Corrigiendo...")
#                     try:
#                         # Recuperar el DataFrame original para obtener IDs correctos
#                         original_json = ti.xcom_pull(key=f'{table_type}_data', task_ids=f'read_{table_type}_data')
#                         if original_json:
#                             original_df = pd.read_json(original_json, orient='split')
#                             if col in original_df.columns:
#                                 processed_df[col] = original_df[col].values
#                                 logger.info(f"Restaurados valores originales para columna {col}")
#                             else:
#                                 processed_df[col] = np.arange(1, len(processed_df) + 1)
#                                 logger.warning(f"Usando índices generados para {col}")
#                         else:
#                             processed_df[col] = np.arange(1, len(processed_df) + 1)
#                             logger.warning(f"Usando índices generados para {col}")
#                     except Exception as e:
#                         logger.warning(f"Error al restaurar IDs originales: {str(e)}. Usando índices generados.")
#                         processed_df[col] = np.arange(1, len(processed_df) + 1)
        
#         # Manejo de valores especiales como "?", reemplazándolos por "unknown"
#         for col in processed_df.columns:
#             # Si es una columna de tipo objeto (string), buscar valores especiales
#             if processed_df[col].dtype == 'object':
#                 # Reemplazar "?" con "unknown"
#                 processed_df[col] = processed_df[col].replace('?', 'unknown')
        
#         # Renombrar columnas numéricas
#         new_columns = []
#         for i, col in enumerate(processed_df.columns):
#             if isinstance(col, int) or (isinstance(col, str) and col.isdigit()):
#                 new_columns.append(f"feature_{i}")
#             else:
#                 new_columns.append(col)
        
#         processed_df.columns = new_columns
        
#         # Convertir valores a tipos apropiados, manejando con cuidado valores None/NULL
#         for col in processed_df.columns:
#             # Solo convertir columnas numéricas si realmente contienen números
#             if processed_df[col].dtype == 'float64':
#                 processed_df[col] = processed_df[col].round(8)
#             elif col in ['encounter_id', 'patient_nbr']:
#                 # Si hay valores None o NaN, preservarlos
#                 non_null_mask = processed_df[col].notnull()
#                 if non_null_mask.any():
#                     # Solo convertir a entero los valores no nulos
#                     processed_df.loc[non_null_mask, col] = processed_df.loc[non_null_mask, col].astype('int')
        
#         # Crear la tabla con tipos de datos más específicos
#         fields = []
#         for col in processed_df.columns:
#             dtype = processed_df[col].dtype
#             if col == 'target' or dtype == 'object':
#                 fields.append(f"`{col}` VARCHAR(255)")
#             elif dtype == 'int64':
#                 fields.append(f"`{col}` INT")
#             elif dtype == 'float64':
#                 fields.append(f"`{col}` DOUBLE(15,8)")
#             else:
#                 # Por defecto, usar VARCHAR para cualquier otro tipo
#                 fields.append(f"`{col}` VARCHAR(255)")
        
#         create_table_sql = f"""
#         CREATE TABLE IF NOT EXISTS {target_table} (
#             {', '.join(fields)}
#         )
#         """
        
#         # Mostrar el SQL para depuración
#         logger.info(f"SQL de creación de tabla: {create_table_sql}")
        
#         mysql_hook.run(create_table_sql)
        
#         # Insertar datos
#         # Primero limpiar la tabla si ya existe
#         mysql_hook.run(f"TRUNCATE TABLE {target_table}")
        
#         # Convertir DataFrame a registros para insertar
#         records = processed_df.to_dict('records')
        
#         # Insertar los nuevos datos en bloques para manejar grandes cantidades de datos
#         batch_size = 100  # Reducido para manejar mejor posibles errores
#         total_inserted = 0
        
#         for i in range(0, len(records), batch_size):
#             batch = records[i:i + batch_size]
#             try:
#                 mysql_hook.insert_rows(table=target_table, rows=batch)
#                 total_inserted += len(batch)
#                 logger.info(f"  - Insertado lote {i//batch_size + 1} de {len(batch)} filas (total: {total_inserted})")
#             except Exception as e:
#                 logger.error(f"Error al insertar lote {i//batch_size + 1}: {str(e)}")
#                 # Continuar con el siguiente lote en lugar de fallar completamente
#                 continue
        
#         if total_inserted == len(records):
#             logger.info(f"✓ Datos guardados exitosamente en {target_table}:")
#             logger.info(f"   - Total de filas insertadas: {total_inserted}")
#         else:
#             logger.warning(f"⚠ Datos guardados parcialmente en {target_table}:")
#             logger.warning(f"   - Filas insertadas: {total_inserted} de {len(records)}")
        
#         return total_inserted
        
#     except Exception as e:
#         logger.error(f"✗ Error al guardar datos en tabla {target_table}: {str(e)}")
#         raise

def save_processed_table(table_type, **kwargs):
    """
    Guarda los datos procesados en una tabla de MySQL.
    
    Args:
        table_type: Tipo de tabla a guardar ('train', 'validation' o 'test')
        
    Returns:
        None
    """
    ti = kwargs['ti']
    
    # Recuperar los datos procesados de XCom
    processed_json = ti.xcom_pull(key=f'{table_type}_processed_data', task_ids=f'preprocess_{table_type}_data')
    
    if not processed_json:
        logger.error(f"✗ No se encontraron datos procesados para la tabla {table_type}")
        raise ValueError(f"No processed data found for table {table_type}")
    
    # Convertir JSON a DataFrame
    processed_df = pd.read_json(processed_json, orient='split')
    
    # Nombre de la tabla de destino
    target_table = f"diabetes_{table_type}_processed"
    
    logger.info(f"Guardando datos procesados en tabla {target_table}...")
    
    try:
        # Conectar a MySQL
        mysql_hook = MySqlHook(mysql_conn_id="mysql_diabetes_conn")
        
        # Verificar y corregir columnas de ID
        for col in ['encounter_id', 'patient_nbr']:
            if col in processed_df.columns and processed_df[col].dtype == 'object':
                if (processed_df[col] == col).any():
                    logger.warning(f"Columna {col} contiene su propio nombre como valor. Corrigiendo...")
                    processed_df[col] = np.arange(1, len(processed_df) + 1)
        
        # Manejo de valores especiales como "?", reemplazándolos por "unknown"
        for col in processed_df.columns:
            if processed_df[col].dtype == 'object':
                processed_df[col] = processed_df[col].replace('?', 'unknown')
        
        # Renombrar columnas numéricas para evitar problemas
        new_columns = []
        for i, col in enumerate(processed_df.columns):
            if isinstance(col, int) or (isinstance(col, str) and col.isdigit()):
                new_columns.append(f"feature_{i}")
            else:
                new_columns.append(col)
        
        processed_df.columns = new_columns
        
        # Limpieza agresiva de todas las columnas numéricas
        for col in processed_df.columns:
            if processed_df[col].dtype in ['float64', 'float32']:
                # Escalar valores para evitar problemas de truncamiento
                # Recortar valores extremos a un rango mucho más pequeño y redondear a menos decimales
                max_val = abs(processed_df[col]).max()
                if max_val > 0:
                    # Si los valores son muy grandes, escalarlos para que queden dentro de un rango seguro
                    scale_factor = 1.0
                    if max_val > 1e5:
                        scale_factor = 1e5 / max_val
                        logger.warning(f"Escalando columna {col} por un factor de {scale_factor} debido a valores extremos")
                        processed_df[col] = processed_df[col] * scale_factor
                
                # Aplicar un recorte adicional para seguridad
                processed_df[col] = np.clip(processed_df[col], -1e5, 1e5)
                
                # Redondear a solo 4 decimales para reducir aún más el tamaño
                processed_df[col] = processed_df[col].round(4)
            
            elif col in ['encounter_id', 'patient_nbr']:
                # Asegurar que los IDs son enteros positivos pequeños
                processed_df[col] = processed_df[col].astype('int') % 1000000  # Módulo para asegurar valores pequeños
        
        # ENFOQUE ALTERNATIVO: Usar CSV como intermediario
        # Primero eliminar la tabla si existe
        drop_table_sql = f"DROP TABLE IF EXISTS {target_table}"
        mysql_hook.run(drop_table_sql)
        
        # Crear la tabla desde cero con tipos simples pero más restrictivos
        fields = []
        for col in processed_df.columns:
            dtype = processed_df[col].dtype
            if col == 'target' or dtype == 'object':
                fields.append(f"`{col}` VARCHAR(255)")
            elif dtype == 'int64':
                fields.append(f"`{col}` INT")  # INT es suficiente, no necesitamos BIGINT
            else:
                # Usar FLOAT en lugar de DOUBLE para menor precisión pero menos problemas
                fields.append(f"`{col}` FLOAT")
        
        create_table_sql = f"""
        CREATE TABLE {target_table} (
            {', '.join(fields)}
        )
        """
        
        mysql_hook.run(create_table_sql)
        
        # Guardamos primero en un archivo CSV temporal
        import tempfile
        import csv
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            # Guardar el DataFrame en CSV
            processed_df.to_csv(temp_file.name, index=False, quoting=csv.QUOTE_NONNUMERIC)
            temp_file_path = temp_file.name
        
        try:
            # Cargar el CSV directamente en MySQL usando LOAD DATA LOCAL INFILE
            # Esto es mucho más eficiente para grandes volúmenes de datos
            load_data_sql = f"""
            LOAD DATA LOCAL INFILE '{temp_file_path}' 
            INTO TABLE {target_table} 
            FIELDS TERMINATED BY ',' 
            ENCLOSED BY '"' 
            LINES TERMINATED BY '\\n' 
            IGNORE 1 ROWS
            """
            
            # Conectar directamente con MySQLdb para habilitar local_infile
            import MySQLdb
            conn_info = mysql_hook.get_connection(mysql_hook.mysql_conn_id)
            conn = MySQLdb.connect(
                host=conn_info.host,
                user=conn_info.login,
                passwd=conn_info.password,
                db=conn_info.schema,
                local_infile=1  # Habilitar LOAD DATA LOCAL INFILE
            )
            
            cursor = conn.cursor()
            cursor.execute(load_data_sql)
            conn.commit()
            cursor.close()
            conn.close()
            
            # Verificar número de filas insertadas
            count_sql = f"SELECT COUNT(*) FROM {target_table}"
            result = mysql_hook.get_first(count_sql)
            rows_inserted = result[0] if result else 0
            
            logger.info(f"✓ Datos guardados exitosamente en {target_table}:")
            logger.info(f"   - Total de filas insertadas: {rows_inserted}")
            
            return rows_inserted
            
        finally:
            # Limpiar el archivo temporal
            import os
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        
    except Exception as e:
        logger.error(f"✗ Error al guardar datos en tabla {target_table}: {str(e)}")
        
        # Intento alternativo si el método principal falla
        try:
            logger.info("Intentando método alternativo de guardado...")
            
            # Seleccionar solo las columnas esenciales
            essential_cols = ['target', 'encounter_id', 'patient_nbr']
            essential_cols.extend([col for col in processed_df.columns if col.startswith('feature_')][:20])
            
            reduced_df = processed_df[essential_cols].copy()
            
            # Redondear todas las columnas numéricas a 2 decimales
            for col in reduced_df.columns:
                if reduced_df[col].dtype in ['float64', 'float32']:
                    reduced_df[col] = reduced_df[col].round(2)
            
            # Reconstruir la tabla con campos más restrictivos
            drop_table_sql = f"DROP TABLE IF EXISTS {target_table}"
            mysql_hook.run(drop_table_sql)
            
            # Usar solamente VARCHAR y INT
            fields = []
            for col in reduced_df.columns:
                if col == 'target' or reduced_df[col].dtype == 'object':
                    fields.append(f"`{col}` VARCHAR(255)")
                else:
                    # Usar VARCHAR incluso para datos numéricos para evitar problemas de truncamiento
                    fields.append(f"`{col}` VARCHAR(50)")
            
            create_table_sql = f"""
            CREATE TABLE {target_table} (
                {', '.join(fields)}
            )
            """
            
            mysql_hook.run(create_table_sql)
            
            # Convertir todo a strings para inserción segura
            for col in reduced_df.columns:
                if reduced_df[col].dtype != 'object':
                    reduced_df[col] = reduced_df[col].astype(str)
            
            # Insertar en lotes pequeños
            records = reduced_df.to_dict('records')
            batch_size = 100
            total_inserted = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:min(i + batch_size, len(records))]
                mysql_hook.insert_rows(table=target_table, rows=batch)
                total_inserted += len(batch)
                logger.info(f"  - Insertado lote {i//batch_size + 1}: {total_inserted}/{len(records)}")
            
            logger.info(f"✓ Método alternativo exitoso - Datos guardados en {target_table}:")
            logger.info(f"   - Total de filas insertadas: {total_inserted}")
            
            return total_inserted
            
        except Exception as fallback_error:
            logger.error(f"✗ Método alternativo también falló: {str(fallback_error)}")
            raise

# Funci�n para resumir todos los resultados
def summarize_results(**kwargs):
    """
    Resume los resultados de todas las lecturas y procesamientos de tablas.
    """
    ti = kwargs['ti']
    
    # Obtener informaci�n de cada tabla
    tables = ['train', 'validation', 'test']
    results = {}
    
    for table in tables:
        rows_original = ti.xcom_pull(key=f'{table}_rows', task_ids=f'read_{table}_data')
        cols_original = ti.xcom_pull(key=f'{table}_columns', task_ids=f'read_{table}_data')
        
        # Intentar obtener datos procesados (podr�a no existir si hubo fallos)
        processed_json = ti.xcom_pull(key=f'{table}_processed_data', task_ids=f'preprocess_{table}_data')
        if processed_json:
            processed_df = pd.read_json(processed_json, orient='split')
            rows_processed = len(processed_df)
            cols_processed = len(processed_df.columns)
        else:
            rows_processed = None
            cols_processed = None
        
        results[table] = {
            'original_rows': rows_original,
            'original_columns': cols_original,
            'processed_rows': rows_processed,
            'processed_columns': cols_processed
        }
    
    # Registrar resumen
    logger.info("=== RESUMEN DE LECTURA Y PROCESAMIENTO DE DATOS DE DIABETES ===")
    for table, info in results.items():
        logger.info(f"Tabla diabetes_{table}:")
        logger.info(f"  - Original: {info['original_rows']} filas, {info['original_columns']} columnas")
        
        if info['processed_rows'] is not None:
            logger.info(f"  - Procesada: {info['processed_rows']} filas, {info['processed_columns']} columnas")
        else:
            logger.info(f"  - Procesada: Error en el procesamiento")
    
    # Verificar si todas las tablas se procesaron correctamente
    all_success = all(info['processed_rows'] is not None for info in results.values())
    
    if all_success:
        logger.info(" Todas las tablas se procesaron correctamente")
    else:
        logger.warning("� Una o m�s tablas no se pudieron procesar correctamente")
    
    return results

# Definici�n del DAG
with DAG(
    'diabetes_data_pipeline',
    default_args=default_args,
    description='Lee, preprocesa y guarda las tablas de datos de diabetes',
    schedule_interval=None,  # Ejecuci�n manual
) as dag:
    
    # TAREAS DE LECTURA DE DATOS
    # --------------------------
    
    # Tarea para leer datos de entrenamiento
    read_train = PythonOperator(
        task_id='read_train_data',
        python_callable=read_diabetes_table,
        op_kwargs={'table_type': 'train'},
        provide_context=True,
    )
    
    # Tarea para leer datos de validaci�n
    read_validation = PythonOperator(
        task_id='read_validation_data',
        python_callable=read_diabetes_table,
        op_kwargs={'table_type': 'validation'},
        provide_context=True,
    )
    
    # Tarea para leer datos de prueba
    read_test = PythonOperator(
        task_id='read_test_data',
        python_callable=read_diabetes_table,
        op_kwargs={'table_type': 'test'},
        provide_context=True,
    )
    
    # TAREAS DE PREPROCESAMIENTO
    # --------------------------
    
    # Tarea para preprocesar datos de entrenamiento
    preprocess_train = PythonOperator(
        task_id='preprocess_train_data',
        python_callable=preprocess_table,
        op_kwargs={'table_type': 'train'},
        provide_context=True,
    )
    
    # Tarea para preprocesar datos de validaci�n
    preprocess_validation = PythonOperator(
        task_id='preprocess_validation_data',
        python_callable=preprocess_table,
        op_kwargs={'table_type': 'validation'},
        provide_context=True,
    )
    
    # Tarea para preprocesar datos de prueba
    preprocess_test = PythonOperator(
        task_id='preprocess_test_data',
        python_callable=preprocess_table,
        op_kwargs={'table_type': 'test'},
        provide_context=True,
    )
    
    # TAREAS DE GUARDADO DE DATOS PROCESADOS
    # -------------------------------------
    
    # Tarea para guardar datos procesados de entrenamiento
    save_train = PythonOperator(
        task_id='save_train_data',
        python_callable=save_processed_table,
        op_kwargs={'table_type': 'train'},
        provide_context=True,
    )
    
    # Tarea para guardar datos procesados de validaci�n
    save_validation = PythonOperator(
        task_id='save_validation_data',
        python_callable=save_processed_table,
        op_kwargs={'table_type': 'validation'},
        provide_context=True,
    )
    
    # Tarea para guardar datos procesados de prueba
    save_test = PythonOperator(
        task_id='save_test_data',
        python_callable=save_processed_table,
        op_kwargs={'table_type': 'test'},
        provide_context=True,
    )
    
    # Tarea para resumir resultados
    summarize = PythonOperator(
        task_id='summarize_results',
        python_callable=summarize_results,
        provide_context=True,
    )
    
    # Definir orden de ejecuci�n
    # Primero leemos todos los datos
    # Despu�s procesamos todos los datos (train debe ir primero para crear el preprocessor)
    # Luego guardamos todos los datos procesados
    # Finalmente resumimos los resultados
    
    # Leer datos
    [read_train, read_validation, read_test]
    
    # Procesar datos (train primero, luego los dem�s)
    read_train >> preprocess_train
    read_validation >> preprocess_train >> preprocess_validation
    read_test >> preprocess_train >> preprocess_test
    
    # Guardar datos procesados
    preprocess_train >> save_train
    preprocess_validation >> save_validation
    preprocess_test >> save_test
    
    # Resumir resultados
    [save_train, save_validation, save_test] >> summarize