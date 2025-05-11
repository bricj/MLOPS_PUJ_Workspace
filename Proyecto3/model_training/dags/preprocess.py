"""
Simple DAG for reading diabetes tables (train, validation, test),
preprocessing them, and saving results to new tables, directly using SQL.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder, OrdinalEncoder
import pickle
import os
import mlflow

# DAG default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# Function to read a table
def read_table(table_type, **context):
    """Read a diabetes table and log its information"""
    table_name = f"diabetes_{table_type}"
    print(f"Reading table {table_name}...")
    
    # Connect to MySQL
    postgres_hook = PostgresHook(postgres_conn_id="postgres_airflow_conn")  # Change to your actual connection ID
    
    # Read the table
    query = f"SELECT * FROM {table_name};"
    df = postgres_hook.get_pandas_df(query)
    
    # Print table info
    print(f"Table {table_name} read successfully:")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print(f"Column names: {', '.join(df.columns.tolist())}")
    
    return True

# Function to preprocess the data and save it
def preprocess_and_save(table_type, **context):
    """Preprocess the diabetes data and save to a new table"""
    # First, read the data directly from the database
    table_name = f"diabetes_{table_type}"
    postgres_hook = PostgresHook(postgres_conn_id="postgres_airflow_conn")
    query = f"SELECT * FROM {table_name}"
    df = postgres_hook.get_pandas_df(query)
    
    print(f"Preprocessing {table_type} data...")
    
    # Process target variable
    y = df['readmitted'].copy()
    y = y.apply(lambda x: 'YES' if x == '<30' or x == '>30' else 'NO')
    
    # Define categorical and numerical columns
    cat_cols = ['race', 'gender', 'age', 'admission_type_id', 'discharge_disposition_id', 
                'admission_source_id', 'diabetesMed', 'max_glu_serum', 'A1Cresult']
    num_cols = ['time_in_hospital', 'num_lab_procedures', 'num_procedures', 'num_medications',
                'number_outpatient', 'number_emergency', 'number_inpatient', 'number_diagnoses']
    
    # Filter to only include columns that exist in the DataFrame
    cat_cols = [col for col in cat_cols if col in df.columns]
    num_cols = [col for col in num_cols if col in df.columns]
    
    # Create X DataFrame with only selected columns
    X = df[cat_cols + num_cols].copy()
    print(f'dataframe after variable selection: {X.shape} ')
    
    # Convert numerical columns to numeric, regardless of original format
    for col in num_cols:
        X[col] = pd.to_numeric(X[col], errors='coerce')
    
    # Fill missing values
    X[cat_cols] = X[cat_cols].fillna('Unknown')
    X[num_cols] = X[num_cols].fillna(0)
    
    # Create preprocessor path
    airflow_home = os.environ.get('AIRFLOW_HOME', '/opt/airflow')
    model_dir = os.path.join(airflow_home, 'data', 'models')
    os.makedirs(model_dir, exist_ok=True)
    preprocessor_path = os.path.join(model_dir, 'diabetes_preprocessor.pkl')
    
    # Create and fit preprocessor

    num_transformer = Pipeline([('scaler', StandardScaler())])
    cat_transformer = Pipeline([('ordinal', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1))])
    
    preprocessor = ColumnTransformer([
        ('num', num_transformer, num_cols),
        ('cat', cat_transformer, cat_cols)
    ])
    
    # Fit and transform
    X_transformed = preprocessor.fit_transform(X)
    
    # Print the first few transformed values to diagnose potential issues
    print(f"First few values of transformed data: {X_transformed[:2, :]}")
    
    # Create processed DataFrame with transformed features
    processed_df = pd.DataFrame(X_transformed)
    
    # Check for problematic values (NaN, infinity) and replace them
    processed_df = processed_df.replace([np.inf, -np.inf], np.nan)
    processed_df = processed_df.fillna(0)
    
    # Rename columns to feature_0, feature_1, etc.
    for i in range(processed_df.shape[1]):
        processed_df.rename(columns={i: f'feature_{i}'}, inplace=True)
    
    # Add the target column
    processed_df['target'] = y.values
    
    # Save directly to database
    target_table = f"diabetes_{table_type}_processed"
    
    # Drop table if exists
    postgres_hook.run(f"DROP TABLE IF EXISTS {target_table}")
    
    # Create new table with appropriate column types - using DOUBLE instead of FLOAT
    columns = []
    for col in processed_df.columns:
        if col == 'target':
            columns.append(f'"{col}" VARCHAR(50)')
        else:
            # Use DOUBLE PRECISION for numerical columns
            columns.append(f'"{col}" DOUBLE PRECISION')
    
    create_table_sql = f"CREATE TABLE {target_table} ({', '.join(columns)})"
    postgres_hook.run(create_table_sql)
    
    # Check for extremely large values that might cause issues
    for col in processed_df.columns:
        if col != 'target':
            max_val = processed_df[col].abs().max()
            if max_val > 1e10:  # If values are extremely large
                print(f"Warning: Column {col} has very large values. Max abs value: {max_val}")
                # Clip extreme values
                processed_df[col] = processed_df[col].clip(-1e10, 1e10)
    
    # Create insert statements directly with a larger batch size
    # try:
        # Create SQL for inserting values
    records = []
    for _, row in processed_df.iterrows():
        values = []
        for col in processed_df.columns:
            if col == 'target':
                values.append(f"'{row[col]}'")
            else:
                # Format numbers with precision
                values.append(str(float(row[col])))
        
        records.append(f"({', '.join(values)})")
    
    # Insert in a single large batch for speed
    batch_size = 15000  # Much larger batch size for faster processing
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        insert_sql = f"INSERT INTO {target_table} ("+', '.join(processed_df.columns.to_list())+f") VALUES {', '.join([str(col) for col in batch])}"
        postgres_hook.run(insert_sql)
        print(f"Inserted batch {i//batch_size + 1}: {len(batch)} rows")

#     engine = postgres_hook.get_sqlalchemy_engine()
#     with engine.begin() as connection:
#         rows_inserted = 0
#         for _, row in processed_df.iterrows():
#             # Filtrar valores None y crear un diccionario limpio
#             values = []
#             for col, value in row.items():
#                 if col == 'target':
#                     values.append(f"'{row[col]}'")
#                 else:
#                     # Format numbers with precision
#                     values.append(str(float(row[col])))
#                 if pd.isna(value) or value =='?':
#                     # Omitir valores nulos o establecer un valor predeterminado
#                     # clean_row[column] = None  # Opción 1: Incluir como NULL
#                     pass  # Opción 2: Omitir columna
#                 else:
#                     clean_row[column.replace('-','_')] = value
            
#             if not clean_row:
#                 continue
            
#             # Construir la consulta SQL con parámetros nombrados
#             columns_str = ', '.join(clean_row.keys())
#             placeholders_str = ', '.join([f':{col}' for col in clean_row.keys()])
#             sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders_str})"
            
#             # Ejecutar la consulta con parámetros nombrados
#             connection.execute(text(sql), clean_row)
#             rows_inserted += 1
        
#         print(f"Insertados {rows_inserted} registros en tabla {table_name} para {dataset_type} batch {batch_number} usando método fila por fila")
# except Exception as e:
#         print(f"Error with direct SQL insert: {str(e)}")
#         # If there's an error, provide detailed diagnostic information
#         if 'feature_0' in str(e):
#             # Check the values in feature_0
#             print("Problematic column: feature_0")
#             print(f"Min value: {processed_df['feature_0'].min()}")
#             print(f"Max value: {processed_df['feature_0'].max()}")
#             print(f"First 5 values: {processed_df['feature_0'].head(5).tolist()}")
        
        # # Try again with more conservative values
        # try:
        #     # Reset the table
        #     postgres_hook.run(f"TRUNCATE TABLE {target_table}")
            
        #     # Convert all feature values to a safe range (-1000 to 1000)
        #     for col in processed_df.columns:
        #         if col != 'target':
        #             processed_df[col] = pd.to_numeric(processed_df[col], errors='coerce').fillna(0)
        #             processed_df[col] = processed_df[col].clip(-1000, 1000)
            
        #     # Insert with smaller batches
        #     records = []
        #     for _, row in processed_df.iterrows():
        #         values = []
        #         for col in processed_df.columns:
        #             if col == 'target':
        #                 values.append(f"'{row[col]}'")
        #             else:
        #                 # Format numbers with precision
        #                 values.append(str(float(row[col])))
                
        #         records.append(f"({', '.join(values)})")
            
        #     # Insert in smaller batches
        #     batch_size = 1000
        #     for i in range(0, len(records), batch_size):
        #         batch = records[i:i+batch_size]
        #         insert_sql = f"INSERT INTO {target_table} ({', '.join('`'+col+'`' for col in processed_df.columns)}) VALUES {', '.join(batch)}"
        #         postgres_hook.run(insert_sql)
        #         print(f"Inserted batch {i//batch_size + 1} (retry): {len(batch)} rows")
            
        #     print("Data inserted successfully with more conservative values")
        # except Exception as e2:
        #     print(f"Fatal error with insert: {str(e2)}")
    
    # Verify the data was inserted correctly
    count_query = f"SELECT COUNT(*) FROM {target_table}"
    result = postgres_hook.get_first(count_query)[0]
    
    print(f"Data saved to {target_table}: {result} rows")
    return True

# Create DAG
with DAG(
    'diabetes_etl_fast',
    default_args=default_args,
    description='ETL pipeline for diabetes data with faster processing',
    schedule_interval=None,  # Manual execution
) as dag:
    
    # Create tasks
    # Read tasks
    # read_train = PythonOperator(
    #     task_id='read_train_data',
    #     python_callable=read_table,
    #     op_kwargs={'table_type': 'train'},
    # )
    
    # read_validation = PythonOperator(
    #     task_id='read_validation_data',
    #     python_callable=read_table,
    #     op_kwargs={'table_type': 'validation'},
    # )
    
    # read_test = PythonOperator(
    #     task_id='read_test_data',
    #     python_callable=read_table,
    #     op_kwargs={'table_type': 'test'},
    # )
    
    # Process and save tasks
    process_save_train = PythonOperator(
        task_id='process_save_train_data',
        python_callable=preprocess_and_save,
        op_kwargs={'table_type': 'train'},
    )
    
    process_save_validation = PythonOperator(
        task_id='process_save_validation_data',
        python_callable=preprocess_and_save,
        op_kwargs={'table_type': 'validation'},
    )
    
    process_save_test = PythonOperator(
        task_id='process_save_test_data',
        python_callable=preprocess_and_save,
        op_kwargs={'table_type': 'test'},
    )
    
    # Define task dependencies
    process_save_train >> process_save_validation >> process_save_test
    # read_validation 
    # read_test             
        
        
    
    # # Make validation and test dependent on train preprocessing
    # process_save_train >> process_save_validation
    # process_save_train >> process_save_test