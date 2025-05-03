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
    
    # DIAGNÓSTICO 1: Verificar los valores únicos en 'readmitted'
    unique_values = df['readmitted'].unique()
    logger.info(f"Valores únicos en readmitted: {unique_values}")
    
    # DIAGNÓSTICO 2: Verificar la distribución original
    original_distribution = df['readmitted'].value_counts()
    logger.info(f"Distribución original de readmitted: {original_distribution.to_dict()}")
    
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
    
    # Process target variable - CORREGIDO
    y = df['readmitted'].copy()  # Usar corchetes simples
    y = y.apply(lambda x: 'YES' if x == '<30' or x == '>30' else 'NO')
    
    # DIAGNÓSTICO 3: Verificar la distribución después de transformar
    new_distribution = y.value_counts()
    logger.info(f"Nueva distribución de target después de transformación: {new_distribution.to_dict()}")
    
    # DIAGNÓSTICO 4: Alerta si solo hay una clase
    if len(new_distribution) == 1:
        logger.warning(f"¡ALERTA! La variable objetivo solo tiene una clase: {new_distribution.index[0]}")
    
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
    
    # Conservar los IDs para poder reconstruir el DataFrame original después
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
    
    # DIAGNÓSTICO: Verificar la distribución de target antes de cualquier transformación
    if 'target' in processed_df.columns:
        target_initial = processed_df['target'].value_counts()
        logger.info(f"Distribución inicial de 'target' en {table_type}: {target_initial.to_dict()}")
    
    try:
        # Conectar a MySQL
        mysql_hook = MySqlHook(mysql_conn_id="mysql_diabetes_conn")
        
        # ENFOQUE SIMPLIFICADO: Crear un DataFrame completamente nuevo con solo las características y target
        
        # 1. Extraer y convertir las columnas de características
        features_df = processed_df.filter(regex='^[0-9]+$|^feature_', axis=1).copy()
        for col in features_df.columns:
            # Convertir todas las columnas de características a string
            features_df[col] = features_df[col].astype(str)
        
        # 2. Crear un DataFrame limpio
        clean_df = pd.DataFrame()
        
        # Añadir columnas de características con nombres limpios
        for i, col in enumerate(features_df.columns):
            clean_df[f'feature_{i}'] = features_df[col]
        
        # Añadir columna target
        if 'target' in processed_df.columns:
            clean_df['target'] = processed_df['target']
        
        # ELIMINAR encounter_id y patient_nbr completamente
        
        # Verificar el DataFrame limpio
        logger.info(f"DataFrame limpio creado con {len(clean_df)} filas y {len(clean_df.columns)} columnas")
        
        # DIAGNÓSTICO: Verificar la distribución final de target
        if 'target' in clean_df.columns:
            target_final = clean_df['target'].value_counts()
            logger.info(f"Distribución final de 'target': {target_final.to_dict()}")
        
        # Primero eliminar la tabla si existe
        drop_table_sql = f"DROP TABLE IF EXISTS {target_table}"
        mysql_hook.run(drop_table_sql)
        
        # Crear la tabla desde cero 
        fields = []
        for col in clean_df.columns:
            if col == 'target':
                fields.append(f"`{col}` VARCHAR(255)")
            else:  # columnas feature_*
                fields.append(f"`{col}` VARCHAR(50)")
        
        create_table_sql = f"""
        CREATE TABLE {target_table} (
            {', '.join(fields)}
        )
        """
        
        mysql_hook.run(create_table_sql)
        
        # Insertar los datos
        # Convertir DataFrame a diccionario de registros
        records = clean_df.to_dict('records')
        
        # Insertar en lotes más pequeños
        batch_size = 50
        total_inserted = 0
        
        for i in range(0, len(records), batch_size):
            batch = records[i:min(i + batch_size, len(records))]
            try:
                mysql_hook.insert_rows(table=target_table, rows=batch)
                total_inserted += len(batch)
                logger.info(f"  - Insertado lote {i//batch_size + 1}: {total_inserted}/{len(records)}")
            except Exception as e:
                logger.error(f"Error al insertar lote {i//batch_size + 1}: {str(e)}")
                if batch:
                    logger.error(f"Primer registro problemático: {batch[0]}")
                continue
        
        # Verificar la distribución de clases en la tabla
        try:
            query = f"SELECT target, COUNT(*) as count FROM {target_table} GROUP BY target"
            result = mysql_hook.get_records(query)
            
            if result:
                target_counts = {str(row[0]): int(row[1]) for row in result}
                logger.info(f"Distribución de 'target' en la tabla guardada: {target_counts}")
            else:
                logger.warning(f"No se pudo verificar la distribución de 'target' en la tabla guardada")
        except Exception as e:
            logger.error(f"Error al verificar distribución en base de datos: {str(e)}")
        
        if total_inserted == len(records):
            logger.info(f"✓ Datos guardados exitosamente en {target_table}:")
            logger.info(f"   - Total de filas insertadas: {total_inserted}")
        else:
            logger.warning(f"⚠ Datos guardados parcialmente en {target_table}:")
            logger.warning(f"   - Filas insertadas: {total_inserted} de {len(records)}")
        
        return total_inserted
        
    except Exception as e:
        logger.error(f"✗ Error al guardar datos en tabla {target_table}: {str(e)}")
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