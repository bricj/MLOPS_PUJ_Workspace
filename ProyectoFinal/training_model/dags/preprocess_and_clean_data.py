"""
DAG para procesamiento de datos desde tablas raw_data
Lee, procesa y guarda en tablas processed
"""

from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from airflow.models import Connection
from airflow.utils.db import provide_session
from datetime import datetime
from airflow.utils.dates import days_ago
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import os

# Configuración
POSTGRES_CONN_ID = "postgres_raw_data"
GROUPS = [3, 4, 5, 6, 7, 8, 9, 10, 1, 2]

default_args = {
    'owner': 'mlops-team',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'retries': 1,
}

dag = DAG(
    'data_processing',
    default_args=default_args,
    description='Procesamiento de datos raw_data a processed',
    schedule_interval=None,  # Manual execution
    catchup=False,
    tags=['processing', 'etl', 'postgresql'],
)

@provide_session
def ensure_postgres_connection(session=None):
    """Asegurar que existe la conexión PostgreSQL"""
    conn = session.query(Connection).filter(Connection.conn_id == POSTGRES_CONN_ID).first()
    
    if not conn:
        new_conn = Connection(
            conn_id=POSTGRES_CONN_ID,
            conn_type='postgres',
            host=os.environ.get('RAW_DATA_DB_HOST', '10.43.101.166'),
            port=int(os.environ.get('RAW_DATA_DB_PORT', '5433')),
            schema=os.environ.get('RAW_DATA_DB_NAME', 'rawdata'),
            login=os.environ.get('RAW_DATA_DB_USER', 'admin'),
            password=os.environ.get('RAW_DATA_DB_PASSWORD', 'admin')
        )
        session.add(new_conn)
        session.commit()
        print("✅ Conexión PostgreSQL creada")
    else:
        print("✅ Conexión PostgreSQL ya existe")

def validate_connection():
    """Validar conectividad a la base de datos"""
    ensure_postgres_connection()
    
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    result = hook.get_first("SELECT current_database();")
    db_name = result[0]
    print(f"✅ Conectado exitosamente a la base de datos: {db_name}")

def get_us_region(state):
    """Mapear estados a regiones de EE.UU."""
    northeast = {'Maine', 'New Hampshire', 'Vermont', 'Massachusetts', 'Rhode Island', 'Connecticut',
                 'New York', 'New Jersey', 'Pennsylvania'}
    
    midwest = {'Ohio', 'Indiana', 'Illinois', 'Michigan', 'Wisconsin',
               'Minnesota', 'Iowa', 'Missouri', 'North Dakota', 'South Dakota', 'Nebraska', 'Kansas'}
    
    south = {'Delaware', 'Maryland', 'District of Columbia', 'Virginia', 'West Virginia',
             'North Carolina', 'South Carolina', 'Georgia', 'Florida',
             'Kentucky', 'Tennessee', 'Mississippi', 'Alabama',
             'Oklahoma', 'Texas', 'Arkansas', 'Louisiana'}
    
    west = {'Montana', 'Idaho', 'Wyoming', 'Colorado', 'New Mexico',
            'Arizona', 'Utah', 'Nevada', 'Washington', 'Oregon', 'California',
            'Alaska', 'Hawaii'}

    if state in northeast:
        return 'Northeast'
    elif state in midwest:
        return 'Midwest'
    elif state in south:
        return 'South'
    elif state in west:
        return 'West'
    else:
        return 'Unknown'

def categorize_cities_by_demand(df, city_col='city'):
    """Categorizar ciudades por demanda"""
    cities = df[city_col].value_counts().reset_index()
    cities.columns = [city_col, 'count']

    def cities_categories(row):
        i = row['count']
        if i <= 50:
            return 'cities-low-demand'
        elif i <= 100:
            return 'cities-midlow-demand'
        elif i <= 500:
            return 'cities-mid-demand'
        else:
            return 'cities-high-demand'

    cities['cities_by_demand'] = cities.apply(cities_categories, axis=1)
    return cities[[city_col, 'cities_by_demand']]

def categorize_transactionality_by_zipcode(df, zip_col='zip_code', date_col='prev_sold_date'):
    """Categorizar códigos postales por transaccionalidad"""
    bought_streets = df[[zip_col, date_col]].copy()
    bought_streets[date_col] = pd.to_datetime(bought_streets[date_col])
    bought_streets['sold_year'] = bought_streets[date_col].dt.year

    grouped = bought_streets.groupby(zip_col)['sold_year'].count()\
        .reset_index(name='num_prev_sales')\
        .sort_values('num_prev_sales')

    def grouped_bought_categories(row):
        i = row['num_prev_sales']
        if i <= 10:
            return 'low_transactionality_zone'
        elif i <= 30:
            return 'mid-low_transactionality_zone'
        elif i <= 50:
            return 'mid_transactionality_zone'
        elif i <= 80:
            return 'mid-high_transactionality_zone'
        else:
            return 'high_transactionality_zone'

    grouped['zone_by_demand'] = grouped.apply(grouped_bought_categories, axis=1)
    return grouped[[zip_col, 'zone_by_demand']]

def categorize_brokered_by_type(df, col='brokered_by'):
    """Categorizar brokers por tipo"""
    brokered = df[col].value_counts().reset_index()
    brokered.columns = [col, 'count']

    def brokered_categories(row):
        i = row['count']
        if i <= 20:
            return 'agent'
        elif i <= 100:
            return 'retail'
        elif i <= 500:
            return 'wholesaler'
        else:
            return 'corporate'

    brokered['broker_type'] = brokered.apply(brokered_categories, axis=1)
    return brokered[[col, 'broker_type']]

def apply_data_processing(df):
    """Aplicar procesamiento completo a los datos"""
    try:
        print("🔄 Iniciando procesamiento de datos...")
        
        # Variables y target
        y = df['price'].copy()
        cat_cols = ['brokered_by', 'city', 'state', 'zip_code']
        num_cols = ['bed', 'bath', 'acre_lot', 'house_size']
        
        # Calcular parámetros categóricos
        print("📊 Calculando parámetros categóricos...")
        cities_parameters = categorize_cities_by_demand(df, city_col='city')
        zipcode_parameters = categorize_transactionality_by_zipcode(df, zip_col='zip_code', date_col='prev_sold_date')
        broker_parameters = categorize_brokered_by_type(df, col='brokered_by')
        
        # Procesar variables categóricas
        print("🏷️ Procesando variables categóricas...")
        df_cat = df[cat_cols].copy()
        df_cat['region'] = df_cat['state'].apply(get_us_region)
        df_cat = df_cat.merge(cities_parameters, how='left', on='city')
        df_cat = df_cat.merge(zipcode_parameters, how='left', on='zip_code')
        df_cat = df_cat.merge(broker_parameters, how='left', on='brokered_by')
        df_cat.drop(columns=['brokered_by', 'city', 'state', 'zip_code'], inplace=True)
        
        # One-hot encoding
        df_cat_encoded = pd.get_dummies(df_cat, drop_first=True).astype(int)
        
        # Limpiar nombres de columnas para PostgreSQL
        df_cat_encoded.columns = [col.replace('-', '_').replace(' ', '_').replace('.', '_') 
                                  for col in df_cat_encoded.columns]
        
        # Procesar variables numéricas
        print("🔢 Procesando variables numéricas...")
        df_num = df[num_cols].copy()
        df_num['rate_bath_bed'] = df['bath'] / df['bed']
        df_num = df_num.drop(columns=['bed', 'bath'], errors='ignore')
        df_num = df_num.applymap(lambda x: np.nan if x <= 0 else x)
        df_num = np.log(df_num)
        df_num = df_num.fillna(df_num.median(numeric_only=True))
        
        # Escalado
        print("⚖️ Aplicando escalado...")
        scaler = MinMaxScaler()
        df_num_scaled = pd.DataFrame(
            scaler.fit_transform(df_num), 
            columns=df_num.columns, 
            index=df_num.index
        )
        
        # Limpiar nombres de columnas numéricas también
        df_num_scaled.columns = [col.replace('-', '_').replace(' ', '_').replace('.', '_') 
                                 for col in df_num_scaled.columns]
        
        # Combinar datos procesados
        processed_df = pd.concat([df_num_scaled, df_cat_encoded], axis=1)
        processed_df['target'] = y.values
        
        print(f"✅ Procesamiento completado:")
        print(f"   - Filas: {len(processed_df)}")
        print(f"   - Columnas: {len(processed_df.columns)}")
        print(f"   - Features numéricas: {len(df_num_scaled.columns)}")
        print(f"   - Features categóricas: {len(df_cat_encoded.columns)}")
        
        return processed_df
        
    except Exception as e:
        print(f"❌ Error en procesamiento: {str(e)}")
        raise e

def save_processed_data(processed_df, group_number):
    """Guardar datos procesados en tabla processed"""
    try:
        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        processed_table_name = f"group_{group_number}_processed"
        
        # Limpiar tabla si existe (evitar duplicados)
        print(f"🧹 Limpiando tabla existente raw_data.{processed_table_name}...")
        hook.run(f"DROP TABLE IF EXISTS raw_data.{processed_table_name};")
        
        # Crear tabla processed
        columns_def = []
        for col in processed_df.columns:
            if col == 'target':
                columns_def.append(f"{col} NUMERIC")
            else:
                columns_def.append(f"{col} NUMERIC")
        
        create_table_sql = f"""
            CREATE TABLE raw_data.{processed_table_name} (
                id SERIAL PRIMARY KEY,
                {', '.join(columns_def)},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        
        hook.run(create_table_sql)
        print(f"✅ Tabla raw_data.{processed_table_name} creada limpia")
        
        # Usar COPY para inserción eficiente
        import io
        csv_buffer = io.StringIO()
        
        for _, row in processed_df.iterrows():
            values = [str(val) for val in row.values]
            csv_line = '\t'.join(values)
            csv_buffer.write(csv_line + '\n')
        
        csv_buffer.seek(0)
        
        # COPY FROM para inserción rápida
        conn = hook.get_conn()
        cursor = conn.cursor()
        
        columns_list = ', '.join(processed_df.columns)
        copy_sql = f"""
            COPY raw_data.{processed_table_name} ({columns_list})
            FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '')
        """
        
        cursor.copy_expert(copy_sql, csv_buffer)
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Datos procesados guardados en raw_data.{processed_table_name}")
        
    except Exception as e:
        print(f"❌ Error guardando datos procesados: {str(e)}")
        raise e

def read_and_process_table(group_number):
    """Leer y procesar una tabla específica"""
    def _read_and_process():
        table_name = f"group_{group_number}_data"
        
        try:
            hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
            
            # Verificar que la tabla existe
            check_table_sql = f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'raw_data' 
                    AND table_name = '{table_name}'
                );
            """
            
            table_exists = hook.get_first(check_table_sql)[0]
            
            if not table_exists:
                print(f"⚠️ Tabla raw_data.{table_name} no existe")
                return
            
            # Contar registros
            count_sql = f"SELECT COUNT(*) FROM raw_data.{table_name};"
            total_records = hook.get_first(count_sql)[0]
            
            if total_records == 0:
                print(f"⚠️ Tabla raw_data.{table_name} está vacía (0 registros)")
                return
            
            print(f"📊 Leyendo tabla raw_data.{table_name} con {total_records} registros...")
            
            # Leer todos los datos de la tabla
            select_sql = f"""
                SELECT 
                    brokered_by, status, price, bed, bath, acre_lot,
                    street, city, state, zip_code, house_size, prev_sold_date,
                    created_at, group_number
                FROM raw_data.{table_name}
                ORDER BY created_at;
            """
            
            # Obtener los datos usando pandas para facilitar el procesamiento
            conn_string = hook.get_uri()
            df = pd.read_sql(select_sql, conn_string)
            
            print(f"✅ Datos leídos exitosamente de raw_data.{table_name}")
            print(f"📋 Columnas: {list(df.columns)}")
            print(f"📊 Registros: {len(df)}")
            print(f"💾 Memoria utilizada: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
            
            # Aplicar procesamiento de datos
            processed_df = apply_data_processing(df)
            
            # Guardar datos procesados
            save_processed_data(processed_df, group_number)
            
            print(f"🎉 Procesamiento de grupo {group_number} completado exitosamente")
            
        except Exception as e:
            print(f"❌ Error leyendo tabla raw_data.{table_name}: {str(e)}")
            print(f"⏭️ Continuando con la siguiente tabla...")
    
    return _read_and_process

def validate_processing_results():
    """Validar resultados del procesamiento"""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    print("📊 Resumen de procesamiento:")
    
    successful_processing = 0
    total_processed_records = 0
    
    for group in GROUPS:
        raw_table = f"group_{group}_data"
        processed_table = f"group_{group}_processed"
        
        try:
            # Verificar tabla raw
            check_raw_sql = f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'raw_data' 
                    AND table_name = '{raw_table}'
                );
            """
            
            # Verificar tabla processed
            check_processed_sql = f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'raw_data' 
                    AND table_name = '{processed_table}'
                );
            """
            
            raw_exists = hook.get_first(check_raw_sql)[0]
            processed_exists = hook.get_first(check_processed_sql)[0]
            
            if raw_exists and processed_exists:
                # Contar registros en ambas tablas
                raw_count = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{raw_table};")[0]
                processed_count = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{processed_table};")[0]
                
                if processed_count > 0:
                    successful_processing += 1
                    total_processed_records += processed_count
                    print(f"   ✅ Grupo {group}: {raw_count} raw → {processed_count} processed")
                else:
                    print(f"   ⚠️ Grupo {group}: Tabla processed vacía")
            elif not raw_exists:
                print(f"   ❌ Grupo {group}: Tabla raw no existe")
            else:
                print(f"   ❌ Grupo {group}: Tabla processed no creada")
                
        except Exception as e:
            print(f"   ❌ Grupo {group}: Error - {str(e)}")
    
    print(f"\n📈 Resumen final de procesamiento:")
    print(f"   - Tablas procesadas exitosamente: {successful_processing}/{len(GROUPS)}")
    print(f"   - Total registros procesados: {total_processed_records:,}")
    
    # Mostrar estructura de una tabla processed (si existe)
    if successful_processing > 0:
        sample_group = GROUPS[0]
        sample_table = f"group_{sample_group}_processed"
        
        try:
            columns_sql = f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'raw_data' 
                AND table_name = '{sample_table}'
                AND column_name != 'id' 
                AND column_name != 'created_at'
                ORDER BY ordinal_position;
            """
            
            columns_info = hook.get_records(columns_sql)
            print(f"\n📋 Estructura de tabla processed (muestra: {sample_table}):")
            for col_name, col_type in columns_info:
                print(f"   - {col_name}: {col_type}")
                
        except Exception as e:
            print(f"⚠️ No se pudo obtener estructura de tabla: {str(e)}")

# Crear tareas del DAG
validate_conn_task = PythonOperator(
    task_id='validate_connection',
    python_callable=validate_connection,
    dag=dag,
)

# Crear tareas de procesamiento para cada grupo
processing_tasks = []
for group in GROUPS:
    task = PythonOperator(
        task_id=f'read_process_group_{group}',
        python_callable=read_and_process_table(group),
        dag=dag,
    )
    processing_tasks.append(task)

validate_results_task = PythonOperator(
    task_id='validate_processing_results',
    python_callable=validate_processing_results,
    dag=dag,
)

# Definir dependencias - procesamiento secuencial
validate_conn_task >> processing_tasks[0]

# Encadenar tareas secuencialmente
for i in range(len(processing_tasks) - 1):
    processing_tasks[i] >> processing_tasks[i + 1]

# Finalizar con validación
processing_tasks[-1] >> validate_results_task