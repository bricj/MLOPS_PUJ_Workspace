"""
Simple DAG for reading diabetes tables (train, validation, test),
preprocessing them, and saving results to new tables, directly using SQL.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
import pickle
import os

# DAG default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 5, 1),
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
    mysql_hook = MySqlHook(mysql_conn_id="mysql_diabetes_conn")
    
    # Read the table
    query = f"SELECT * FROM {table_name}"
    df = mysql_hook.get_pandas_df(query)
    
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
    mysql_hook = MySqlHook(mysql_conn_id="mysql_diabetes_conn")
    query = f"SELECT * FROM {table_name}"
    df = mysql_hook.get_pandas_df(query)
    
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
    if table_type == 'train':
        # For train data, create a new preprocessor
        num_transformer = Pipeline([('scaler', StandardScaler())])
        cat_transformer = Pipeline([('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))])
        
        preprocessor = ColumnTransformer([
            ('num', num_transformer, num_cols),
            ('cat', cat_transformer, cat_cols)
        ])
        
        # Fit and transform
        X_transformed = preprocessor.fit_transform(X)
        
        # Save preprocessor
        print(f"Saving preprocessor to {preprocessor_path}")
        try:
            with open(preprocessor_path, 'wb') as f:
                pickle.dump(preprocessor, f)
            print("Preprocessor saved successfully")
        except Exception as e:
            print(f"Error saving preprocessor: {str(e)}")
    else:
        # For validation/test, use the train preprocessor
        try:
            print(f"Loading preprocessor from {preprocessor_path}")
            with open(preprocessor_path, 'rb') as f:
                preprocessor = pickle.load(f)
            print("Preprocessor loaded successfully")
            
            # Transform using loaded preprocessor
            X_transformed = preprocessor.transform(X)
        except FileNotFoundError:
            # If preprocessor not found, create a new one
            print("Preprocessor not found. Creating a new one.")
            num_transformer = Pipeline([('scaler', StandardScaler())])
            cat_transformer = Pipeline([('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))])
            
            preprocessor = ColumnTransformer([
                ('num', num_transformer, num_cols),
                ('cat', cat_transformer, cat_cols)
            ])
            
            # Fit and transform
            X_transformed = preprocessor.fit_transform(X)
    
    # Print the first few transformed values to diagnose potential issues
    print(f"First few values of transformed data: {X_transformed[:2, :5]}")
    
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
    mysql_hook.run(f"DROP TABLE IF EXISTS {target_table}")
    
    # Create new table with appropriate column types - using DOUBLE instead of FLOAT
    columns = []
    for col in processed_df.columns:
        if col == 'target':
            columns.append(f"`{col}` VARCHAR(50)")
        else:
            # Use DOUBLE type for all processed numerical columns for better precision
            columns.append(f"`{col}` DOUBLE")
    
    create_table_sql = f"CREATE TABLE {target_table} ({', '.join(columns)})"
    mysql_hook.run(create_table_sql)
    
    # Check for extremely large values that might cause issues
    for col in processed_df.columns:
        if col != 'target':
            max_val = processed_df[col].abs().max()
            if max_val > 1e10:  # If values are extremely large
                print(f"Warning: Column {col} has very large values. Max abs value: {max_val}")
                # Clip extreme values
                processed_df[col] = processed_df[col].clip(-1e10, 1e10)
    
    # Create insert statements directly with a larger batch size
    try:
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
        batch_size = 5000  # Much larger batch size for faster processing
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            insert_sql = f"INSERT INTO {target_table} ({', '.join('`'+col+'`' for col in processed_df.columns)}) VALUES {', '.join(batch)}"
            mysql_hook.run(insert_sql)
            print(f"Inserted batch {i//batch_size + 1}: {len(batch)} rows")
    
    except Exception as e:
        print(f"Error with direct SQL insert: {str(e)}")
        # If there's an error, provide detailed diagnostic information
        if 'feature_0' in str(e):
            # Check the values in feature_0
            print("Problematic column: feature_0")
            print(f"Min value: {processed_df['feature_0'].min()}")
            print(f"Max value: {processed_df['feature_0'].max()}")
            print(f"First 5 values: {processed_df['feature_0'].head(5).tolist()}")
        
        # Try again with more conservative values
        try:
            # Reset the table
            mysql_hook.run(f"TRUNCATE TABLE {target_table}")
            
            # Convert all feature values to a safe range (-1000 to 1000)
            for col in processed_df.columns:
                if col != 'target':
                    processed_df[col] = pd.to_numeric(processed_df[col], errors='coerce').fillna(0)
                    processed_df[col] = processed_df[col].clip(-1000, 1000)
            
            # Insert with smaller batches
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
            
            # Insert in smaller batches
            batch_size = 1000
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                insert_sql = f"INSERT INTO {target_table} ({', '.join('`'+col+'`' for col in processed_df.columns)}) VALUES {', '.join(batch)}"
                mysql_hook.run(insert_sql)
                print(f"Inserted batch {i//batch_size + 1} (retry): {len(batch)} rows")
            
            print("Data inserted successfully with more conservative values")
        except Exception as e2:
            print(f"Fatal error with insert: {str(e2)}")
    
    # Verify the data was inserted correctly
    count_query = f"SELECT COUNT(*) FROM {target_table}"
    result = mysql_hook.get_first(count_query)[0]
    
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
    read_train = PythonOperator(
        task_id='read_train_data',
        python_callable=read_table,
        op_kwargs={'table_type': 'train'},
    )
    
    read_validation = PythonOperator(
        task_id='read_validation_data',
        python_callable=read_table,
        op_kwargs={'table_type': 'validation'},
    )
    
    read_test = PythonOperator(
        task_id='read_test_data',
        python_callable=read_table,
        op_kwargs={'table_type': 'test'},
    )
    
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
    read_train >> process_save_train
    read_validation >> process_save_validation
    read_test >> process_save_test
    
    # Make validation and test dependent on train preprocessing
    process_save_train >> process_save_validation
    process_save_train >> process_save_test