import os
from airflow import DAG
from airflow.operators.python import PythonOperator
import psycopg2

# Configuración de conexión (disponible en todos los DAGs)
RAW_DATA_CONFIG = {
    'host': os.environ.get('RAW_DATA_DB_HOST'),
    'port': os.environ.get('RAW_DATA_DB_PORT'),
    'database': os.environ.get('RAW_DATA_DB_NAME'),
    'user': os.environ.get('RAW_DATA_DB_USER'),
    'password': os.environ.get('RAW_DATA_DB_PASSWORD')
}

def create_table_task():
    conn = psycopg2.connect(**RAW_DATA_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mi_tabla (
            id SERIAL PRIMARY KEY,
            data VARCHAR(255)
        );
    """)
    conn.commit()
    conn.close()