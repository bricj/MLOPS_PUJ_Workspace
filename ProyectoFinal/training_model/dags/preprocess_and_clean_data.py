# """
# DAG para procesamiento de datos desde tablas raw_data
# Lee, procesa y guarda en tablas processed - VERSION DEPURADA
# """

# from airflow import DAG
# from airflow.providers.postgres.hooks.postgres import PostgresHook
# from airflow.operators.python import PythonOperator
# from airflow.models import Connection
# from airflow.utils.db import provide_session
# from datetime import datetime
# from airflow.utils.dates import days_ago
# import pandas as pd
# import numpy as np
# from sklearn.preprocessing import MinMaxScaler
# import os
# import io

# # Configuración
# POSTGRES_CONN_ID = "postgres_raw_data"

# default_args = {
#     'owner': 'mlops-team',
#     'depends_on_past': False,
#     'start_date': days_ago(1),
#     'email_on_failure': False,
#     'retries': 1,
# }

# dag = DAG(
#     'data_processing',
#     default_args=default_args,
#     description='Procesamiento de datos raw_data a processed',
#     schedule_interval=None,
#     catchup=False,
#     tags=['processing', 'etl', 'postgresql'],
# )

# @provide_session
# def setup_connection(session=None):
#     """Configurar conexión PostgreSQL"""
#     if not session.query(Connection).filter(Connection.conn_id == POSTGRES_CONN_ID).first():
#         conn = Connection(
#             conn_id=POSTGRES_CONN_ID,
#             conn_type='postgres',
#             host=os.environ.get('RAW_DATA_DB_HOST', '10.43.101.166'),
#             port=int(os.environ.get('RAW_DATA_DB_PORT', '5433')),
#             schema=os.environ.get('RAW_DATA_DB_NAME', 'rawdata'),
#             login=os.environ.get('RAW_DATA_DB_USER', 'admin'),
#             password=os.environ.get('RAW_DATA_DB_PASSWORD', 'admin')
#         )
#         session.add(conn)
#         session.commit()

# def get_us_region(state):
#     """Mapear estados a regiones de EE.UU."""
#     if pd.isna(state):
#         return 'Unknown'
#     if pd.isna(state):
#         return 'Unknown'
        
#     northeast = {'Maine', 'New Hampshire', 'Vermont', 'Massachusetts', 'Rhode Island', 'Connecticut',
#                  'New York', 'New Jersey', 'Pennsylvania'}
    
#     midwest = {'Ohio', 'Indiana', 'Illinois', 'Michigan', 'Wisconsin',
#                'Minnesota', 'Iowa', 'Missouri', 'North Dakota', 'South Dakota', 'Nebraska', 'Kansas'}
    
#     south = {'Delaware', 'Maryland', 'District of Columbia', 'Virginia', 'West Virginia',
#              'North Carolina', 'South Carolina', 'Georgia', 'Florida',
#              'Kentucky', 'Tennessee', 'Mississippi', 'Alabama',
#              'Oklahoma', 'Texas', 'Arkansas', 'Louisiana'}
    
#     west = {'Montana', 'Idaho', 'Wyoming', 'Colorado', 'New Mexico',
#             'Arizona', 'Utah', 'Nevada', 'Washington', 'Oregon', 'California',
#             'Alaska', 'Hawaii'}

#     if state in northeast:
#         return 'Northeast'
#     elif state in midwest:
#         return 'Midwest'
#     elif state in south:
#         return 'South'
#     elif state in west:
#         return 'West'
#     else:
#         return 'Unknown'

# # def categorize_cities_by_demand(df, city_col='city'):
# #     """Categorizar ciudades por demanda"""
# #     valid_df = df[df[city_col].notna()].copy()
# #     if len(valid_df) == 0:
# #         return pd.DataFrame({city_col: [], 'cities_by_demand': []})
# #     cities = valid_df[city_col].value_counts().reset_index()
# #     cities.columns = [city_col, 'count']

# #     def cities_categories(row):
# #         i = row['count']
# #         if i <= 50:
# #             return 'cities-low-demand'
# #         elif i <= 100:
# #             return 'cities-midlow-demand'
# #         elif i <= 500:
# #             return 'cities-mid-demand'
# #         else:
# #             return 'cities-high-demand'

# #     cities['cities_by_demand'] = cities.apply(cities_categories, axis=1)
# #     return cities[[city_col, 'cities_by_demand']]

# def categorize_cities_by_demand(df, city_col='city'):
#     """Categorizar ciudades por demanda con 12 categorías granulares"""
#     valid_df = df[df[city_col].notna()].copy()
#     if len(valid_df) == 0:
#         return pd.DataFrame({city_col: [], 'cities_by_demand': []})
#     cities = valid_df[city_col].value_counts().reset_index()
#     cities.columns = [city_col, 'count']

#     def cities_categories(row):
#         i = row['count']
#         if i <= 10:
#             return 'cities_minimal_demand'        # 1-10 propiedades
#         elif i <= 25:
#             return 'cities_very_low_demand'       # 11-25 propiedades
#         elif i <= 50:
#             return 'cities_low_demand'            # 26-50 propiedades
#         elif i <= 100:
#             return 'cities_low_mid_demand'        # 51-100 propiedades
#         elif i <= 200:
#             return 'cities_mid_demand'            # 101-200 propiedades
#         elif i <= 400:
#             return 'cities_mid_high_demand'       # 201-400 propiedades
#         elif i <= 800:
#             return 'cities_high_demand'           # 401-800 propiedades
#         elif i <= 1500:
#             return 'cities_very_high_demand'      # 801-1500 propiedades
#         elif i <= 3000:
#             return 'cities_premium_demand'        # 1501-3000 propiedades
#         elif i <= 5000:
#             return 'cities_mega_demand'           # 3001-5000 propiedades
#         elif i <= 8000:
#             return 'cities_ultra_demand'          # 5001-8000 propiedades
#         else:
#             return 'cities_massive_demand'        # 8000+ propiedades

#     cities['cities_by_demand'] = cities.apply(cities_categories, axis=1)
#     return cities[[city_col, 'cities_by_demand']]

# def categorize_transactionality_by_zipcode(df, zip_col='zip_code', date_col='prev_sold_date'):
#     """Categorizar códigos postales por transaccionalidad"""
#     bought_streets = df[[zip_col, date_col]].copy()
    
#     # Manejo robusto de fechas
#     bought_streets[date_col] = pd.to_datetime(bought_streets[date_col], errors='coerce')
    
#     # Filtrar datos válidos
#     valid_data = bought_streets[
#         bought_streets[zip_col].notna() & 
#         bought_streets[date_col].notna()
#     ].copy()
    
#     if len(valid_data) == 0:
#         return pd.DataFrame({zip_col: [], 'zone_by_demand': []})
    
#     valid_data['sold_year'] = valid_data[date_col].dt.year
    
#     grouped = valid_data.groupby(zip_col)['sold_year'].count()\
#         .reset_index(name='num_prev_sales')\
#         .sort_values('num_prev_sales')

#     # def grouped_bought_categories(row):
#     #     i = row['num_prev_sales']
#     #     if i <= 10:
#     #         return 'low_transactionality_zone'
#     #     elif i <= 30:
#     #         return 'mid-low_transactionality_zone'
#     #     elif i <= 50:
#     #         return 'mid_transactionality_zone'
#     #     elif i <= 80:
#     #         return 'mid-high_transactionality_zone'
#     #     else:
#     #         return 'high_transactionality_zone'

#     def grouped_bought_categories(row):
#         i = row['num_prev_sales']
#         if i <= 80:
#             return 'minimal_transactionality_zone'     # 1-5 ventas
#         elif i <= 200:
#             return 'very_low_transactionality_zone'    # 6-15 ventas
#         elif i <= 400:
#             return 'low_transactionality_zone'         # 16-30 ventas
#         elif i <= 600:
#             return 'low_mid_transactionality_zone'     # 31-50 ventas
#         elif i <= 1000:
#             return 'mid_transactionality_zone'         # 51-80 ventas
#         elif i <= 1500:
#             return 'mid_high_transactionality_zone'    # 81-120 ventas
#         elif i <= 2000:
#             return 'high_transactionality_zone'        # 121-200 ventas
#         elif i <= 3000:
#             return 'very_high_transactionality_zone'   # 201-350 ventas
#         elif i <= 4000:
#             return 'premium_transactionality_zone'     # 351-600 ventas
#         else:
#             return 'mega_transactionality_zone'        # 600+ ventas

#     grouped['zone_by_demand'] = grouped.apply(grouped_bought_categories, axis=1)
#     return grouped[[zip_col, 'zone_by_demand']]

# def categorize_brokered_by_type(df, col='brokered_by'):
#     """Categorizar brokers por tipo"""
#     # Filtrar valores válidos
#     valid_df = df[df[col].notna() & (df[col] != '')].copy()
#     if len(valid_df) == 0:
#         return pd.DataFrame({col: [], 'broker_type': []})
    
#     brokered = valid_df[col].value_counts().reset_index()
#     brokered.columns = [col, 'count']

#     # def brokered_categories(row):
#     #     i = row['count']
#     #     if i <= 20:
#     #         return 'agent'
#     #     elif i <= 100:
#     #         return 'retail'
#     #     elif i <= 500:
#     #         return 'wholesaler'
#     #     else:
#     #         return 'corporate'

#     def brokered_categories(row):
#         i = row['count']
#         if i <= 500:
#             return 'micro_agent'           # 1-5 propiedades
#         elif i <= 750:
#             return 'small_agent'           # 6-15 propiedades
#         elif i <= 1000:
#             return 'agent'                 # 16-35 propiedades
#         elif i <= 1300:
#             return 'senior_agent'          # 36-70 propiedades
#         elif i <= 1500:
#             return 'retail_broker'         # 71-150 propiedades
#         elif i <= 2000:
#             return 'regional_broker'       # 151-300 propiedades
#         elif i <= 3000:
#             return 'wholesaler'            # 301-600 propiedades
#         elif i <= 4000:
#             return 'major_wholesaler'      # 601-1200 propiedades
#         elif i <= 5000:
#             return 'corporate'             # 1201-2500 propiedades
#         else:
#             return 'mega_corporate'        # 2500+ propiedades

#     brokered['broker_type'] = brokered.apply(brokered_categories, axis=1)
#     return brokered[[col, 'broker_type']]

# def apply_data_processing(df):
#     """Aplicar procesamiento completo a los datos"""
#     print("🔧 Iniciando procesamiento de datos...")
    
#     y = df['price'].copy()
#     cat_cols = ['brokered_by', 'city', 'state', 'zip_code']
#     num_cols = ['bed', 'bath', 'acre_lot', 'house_size']
    
#     # Limpieza ROBUSTA de categóricas - manejo completo de NA
#     df_clean = df.copy()
#     print("🧹 Tratamiento de valores NA:")
#     for col in cat_cols:
#         na_before = df_clean[col].isnull().sum()
#         empty_before = (df_clean[col] == '').sum() if df_clean[col].dtype == 'object' else 0
        
#         # Tratamiento completo de valores faltantes/vacíos
#         df_clean[col] = df_clean[col].fillna('Unknown')  # NaN → 'Unknown'
#         if df_clean[col].dtype == 'object':
#             df_clean[col] = df_clean[col].replace(['', ' ', 'null', 'NULL', 'nan', 'NaN', '0'], 'Unknown')
#             df_clean[col] = df_clean[col].str.strip()  # Eliminar espacios
        
#         na_after = (df_clean[col] == 'Unknown').sum()
#         print(f"   {col}: {na_before} NaN + {empty_before} vacíos → {na_after} Unknown")
    
#     # Generar parámetros de categorización con DEBUG
#     print("📊 Generando parámetros de categorización...")
#     cities_parameters = categorize_cities_by_demand(df_clean, city_col='city')
#     print(f"   Cities parameters: {cities_parameters.shape} - {cities_parameters['cities_by_demand'].nunique()} categorías")
    
#     zipcode_parameters = categorize_transactionality_by_zipcode(df_clean, zip_col='zip_code', date_col='prev_sold_date')
#     print(f"   Zipcode parameters: {zipcode_parameters.shape} - {zipcode_parameters['zone_by_demand'].nunique() if len(zipcode_parameters) > 0 else 0} categorías")
    
#     broker_parameters = categorize_brokered_by_type(df_clean, col='brokered_by')
#     print(f"   Broker parameters: {broker_parameters.shape} - {broker_parameters['broker_type'].nunique() if len(broker_parameters) > 0 else 0} categorías")
    
#     # Procesar categóricas
#     df_cat = df_clean[cat_cols].copy()
#     print(f"🏷️  df_cat inicial: {df_cat.shape}")
#     df_cat['region'] = df_cat['state'].apply(get_us_region)
#     print(f"   Después de agregar region: {df_cat.shape} - {df_cat['region'].nunique()} regiones únicas")
    
#     # Merges con validación y DEBUG
#     print("🔗 Realizando merges...")
#     df_cat = df_cat.merge(cities_parameters, how='left', on='city')
#     print(f"   Después de merge cities: {df_cat.shape} - NaN en cities_by_demand: {df_cat['cities_by_demand'].isnull().sum()}")
    
#     df_cat = df_cat.merge(zipcode_parameters, how='left', on='zip_code')
#     if 'zone_by_demand' in df_cat.columns:
#         print(f"   Después de merge zipcode: {df_cat.shape} - NaN en zone_by_demand: {df_cat['zone_by_demand'].isnull().sum()}")
#     else:
#         print(f"   Después de merge zipcode: {df_cat.shape} - ⚠️ zone_by_demand NO SE CREÓ")
    
#     df_cat = df_cat.merge(broker_parameters, how='left', on='brokered_by')
#     if 'broker_type' in df_cat.columns:
#         print(f"   Después de merge broker: {df_cat.shape} - NaN en broker_type: {df_cat['broker_type'].isnull().sum()}")
#     else:
#         print(f"   Después de merge broker: {df_cat.shape} - ⚠️ broker_type NO SE CREÓ")
    
#     # Manejar NaN resultantes de merges
#     for col in ['cities_by_demand', 'zone_by_demand', 'broker_type']:
#         if col in df_cat.columns:
#             df_cat[col] = df_cat[col].fillna('Unknown')
    
#     df_cat.drop(columns=['brokered_by', 'city', 'state', 'zip_code'], inplace=True)
#     print(f"   Después de drop columnas: {df_cat.shape}")
#     print(f"   Columnas para encoding: {list(df_cat.columns)}")
    
#     # DEBUG detallado antes de get_dummies
#     for col in df_cat.columns:
#         unique_vals = df_cat[col].nunique()
#         print(f"   {col}: {unique_vals} valores únicos")
    
#     # Encoding categórico - CAMBIO CRÍTICO: drop_first=False para datos con poca variabilidad
#     df_cat_encoded = pd.get_dummies(df_cat, drop_first=False).astype(int)
#     print(f"🎯 get_dummies resultado: {df_cat_encoded.shape}")
#     print(f"   Columnas generadas: {list(df_cat_encoded.columns)}")
    
#     # Limpiar nombres de columnas para PostgreSQL
#     df_cat_encoded.columns = [col.replace('-', '_').replace(' ', '_').replace('.', '_') 
#                               for col in df_cat_encoded.columns]
    
#     # Procesar numéricas
#     df_num = df_clean[num_cols].copy()
#     df_num['rate_bath_bed'] = df_clean['bath'] / df_clean['bed'].replace(0, 1)  # Evitar división por 0
#     df_num = df_num.drop(columns=['bed', 'bath'], errors='ignore')
#     df_num = df_num.applymap(lambda x: np.nan if x <= 0 else x)
#     df_num = np.log(df_num)
#     df_num = df_num.fillna(df_num.median(numeric_only=True))
    
#     # Escalado
#     scaler = MinMaxScaler()
#     df_num_scaled = pd.DataFrame(scaler.fit_transform(df_num), columns=df_num.columns, index=df_num.index)
    
#     # Limpiar nombres de columnas numéricas
#     df_num_scaled.columns = [col.replace('-', '_').replace(' ', '_').replace('.', '_') 
#                              for col in df_num_scaled.columns]
    
#     # Combinar resultado final
#     processed_df = pd.concat([df_num_scaled, df_cat_encoded], axis=1)
#     processed_df['target'] = y.values
    
#     print(f"✅ Procesamiento completado: {len(processed_df)} filas, {len(processed_df.columns)} columnas")
    
#     return processed_df

# def process_data(**context):
#     """Leer datos raw, procesarlos y guardarlos como processed"""
#     start_time = datetime.now()
#     setup_connection()
#     hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
#     batch_number = context['dag_run'].conf.get('batch_number', 1) if context['dag_run'].conf else 1
#     raw_table = f"api_data_batch_{batch_number}"
#     processed_table = f"api_data_batch_{batch_number}_processed"
    
#     # Verificar tabla origen
#     check_table_sql = f"""
#         SELECT EXISTS (
#             SELECT FROM information_schema.tables 
#             WHERE table_schema = 'raw_data' 
#             AND table_name = '{raw_table}'
#         );
#     """
    
#     if not hook.get_first(check_table_sql)[0]:
#         print(f"❌ Tabla raw_data.{raw_table} no existe")
#         return
    
#     count = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{raw_table};")[0]
#     if count == 0:
#         print(f"❌ Tabla raw_data.{raw_table} está vacía")
#         return
    
#     print(f"📊 Leyendo {count:,} registros de raw_data.{raw_table}...")
    
#     # Leer datos
#     select_sql = f"""
#         SELECT 
#             brokered_by, status, price, bed, bath, acre_lot,
#             street, city, state, zip_code, house_size, prev_sold_date
#         FROM raw_data.{raw_table}
#         ORDER BY created_at;
#     """
    
#     conn_string = hook.get_uri()
#     df = pd.read_sql(select_sql, conn_string)
    
#     # Debug: Información del DataFrame leído
#     print(f"📋 DATOS LEÍDOS:")
#     print(f"   Shape: {df.shape[0]:,} filas x {df.shape[1]} columnas")
#     print(f"   Columnas: {list(df.columns)}")
#     print(f"   Tipos de datos: {dict(df.dtypes)}")
    
#     # Aplicar procesamiento
#     processed_df = apply_data_processing(df)
    
#     # Crear tabla procesada
#     hook.run(f"DROP TABLE IF EXISTS raw_data.{processed_table} CASCADE;")
    
#     columns_def = [f"{col} NUMERIC" for col in processed_df.columns]
#     create_table_sql = f"""
#         CREATE TABLE raw_data.{processed_table} (
#             id SERIAL PRIMARY KEY,
#             {', '.join(columns_def)},
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         );
#     """
#     hook.run(create_table_sql)
    
#     # Insertar datos usando COPY
#     csv_buffer = io.StringIO()
#     for _, row in processed_df.iterrows():
#         values = [str(val) for val in row.values]
#         csv_buffer.write('\t'.join(values) + '\n')
    
#     csv_buffer.seek(0)
    
#     conn = hook.get_conn()
#     cursor = conn.cursor()
    
#     columns_list = ', '.join(processed_df.columns)
#     copy_sql = f"""
#         COPY raw_data.{processed_table} ({columns_list})
#         FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '')
#     """
    
#     cursor.copy_expert(copy_sql, csv_buffer)
#     conn.commit()
#     cursor.close()
#     conn.close()
    
#     # Métricas
#     execution_time = (datetime.now() - start_time).total_seconds()
#     size_mb = (len(processed_df) * len(processed_df.columns) * 8) / (1024 * 1024)
    
#     print(f"📈 MÉTRICAS:")
#     print(f"   Filas: {len(processed_df):,}")
#     print(f"   Features: {len(processed_df.columns):,}")
#     print(f"   Tamaño: {size_mb:.2f} MB")
#     print(f"   Tiempo: {execution_time:.2f} seg")
#     print(f"   Velocidad: {len(processed_df)/execution_time:,.0f} filas/seg")

# def validate_processed_data(**context):
#     """Validar datos procesados"""
#     batch_number = context['dag_run'].conf.get('batch_number', 1) if context['dag_run'].conf else 1
#     processed_table = f"api_data_batch_{batch_number}_processed"
    
#     hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
#     count = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{processed_table};")[0]
    
#     if count > 0:
#         columns_sql = f"""
#             SELECT COUNT(*) as num_columns
#             FROM information_schema.columns 
#             WHERE table_schema = 'raw_data' 
#             AND table_name = '{processed_table}'
#             AND column_name NOT IN ('id', 'created_at');
#         """
#         num_columns = hook.get_first(columns_sql)[0]
        
#         print(f"✅ Datos procesados exitosamente:")
#         print(f"   Registros: {count:,}")
#         print(f"   Features: {num_columns}")
#         print(f"   Tabla: raw_data.{processed_table}")
#     else:
#         print("❌ No se procesaron datos")

# # Tareas
# process_task = PythonOperator(task_id='process_data', python_callable=process_data, dag=dag)
# validate_task = PythonOperator(task_id='validate_processed_data', python_callable=validate_processed_data, dag=dag)

# # Flujo
# process_task >> validate_task
"""
DAG para procesamiento de datos desde tablas raw_data
Lee, procesa y guarda en tablas processed - VERSION MEJORADA CON LÍMITES TOTALMENTE DINÁMICOS
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
import io
import math

# Configuración
POSTGRES_CONN_ID = "postgres_raw_data"

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
    description='Procesamiento de datos raw_data a processed con límites totalmente dinámicos',
    schedule_interval=None,
    catchup=False,
    tags=['processing', 'etl', 'postgresql'],
)

@provide_session
def setup_connection(session=None):
    """Configurar conexión PostgreSQL"""
    if not session.query(Connection).filter(Connection.conn_id == POSTGRES_CONN_ID).first():
        conn = Connection(
            conn_id=POSTGRES_CONN_ID,
            conn_type='postgres',
            host=os.environ.get('RAW_DATA_DB_HOST', '10.43.101.166'),
            port=int(os.environ.get('RAW_DATA_DB_PORT', '5433')),
            schema=os.environ.get('RAW_DATA_DB_NAME', 'rawdata'),
            login=os.environ.get('RAW_DATA_DB_USER', 'admin'),
            password=os.environ.get('RAW_DATA_DB_PASSWORD', 'admin')
        )
        session.add(conn)
        session.commit()

def get_us_region(state):
    """Mapear estados a regiones de EE.UU."""
    if pd.isna(state):
        return 'Unknown'
        
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

def analyze_distribution_stats(series, column_name):
    """Función auxiliar para mostrar estadísticas detalladas de distribución"""
    print(f"\n📊 ANÁLISIS DE DISTRIBUCIÓN - {column_name.upper()}:")
    print("=" * 60)
    
    if series.dtype in ['object', 'string']:
        # Para variables categóricas
        value_counts = series.value_counts()
        print(f"   📋 Valores únicos: {series.nunique()}")
        print(f"   📊 Top 10 valores más frecuentes:")
        for i, (value, count) in enumerate(value_counts.head(10).items()):
            percentage = (count / len(series)) * 100
            print(f"      {i+1:2d}. {value}: {count:,} ({percentage:.1f}%)")
        
        if len(value_counts) > 10:
            others_count = sum(value_counts.iloc[10:])
            others_pct = (others_count / len(series)) * 100
            print(f"       ... otros {len(value_counts)-10} valores: {others_count:,} ({others_pct:.1f}%)")
    else:
        # Para variables numéricas
        print(f"   📈 Estadísticas básicas:")
        print(f"      Count: {series.count():,}")
        print(f"      Valores nulos: {series.isnull().sum():,}")
        print(f"      Mínimo: {series.min():,.2f}")
        print(f"      Q25: {series.quantile(0.25):,.2f}")
        print(f"      Mediana: {series.median():,.2f}")
        print(f"      Q75: {series.quantile(0.75):,.2f}")
        print(f"      Máximo: {series.max():,.2f}")
        print(f"      Media: {series.mean():.2f}")
        print(f"      Desv. Std: {series.std():.2f}")
        
        # Percentiles adicionales para identificar puntos de corte
        print(f"   🎯 Percentiles clave para categorización:")
        percentiles = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99]
        for p in percentiles:
            val = series.quantile(p/100)
            print(f"      P{p:2d}: {val:,.0f}")

# =============================================================================
# NUEVA FUNCIÓN: LÍMITES TOTALMENTE DINÁMICOS
# =============================================================================

def calculate_adaptive_limits(total_records):
    """
    Calcular límites adaptativos usando función logarítmica continua basada en el tamaño del dataset.
    Escala suavemente para cualquier tamaño de dataset sin categorías discretas.
    """
    print(f"\n🎯 CALCULANDO LÍMITES ADAPTATIVOS DINÁMICOS:")
    print("=" * 45)
    print(f"   📊 Dataset size: {total_records:,} registros")
    
    # Factores de escala para cada tipo de entidad
    # Estos factores ajustan la proporción relativa entre límites de cada entidad
    city_factor = 1.0       # Base de referencia
    zipcode_factor = 0.4    # Códigos postales tienen menos propiedades que ciudades
    broker_factor = 0.2     # Brokers suelen tener menos propiedades que códigos postales
    
    # Función base logarítmica para calcular límites
    # Usamos log para que el crecimiento sea sublineal con el tamaño del dataset
    # La constante 1000 se usa para normalizar y puede ajustarse según necesidad
    def calculate_base_limit(records, quantile):
        # Añadimos 1000 para evitar valores muy pequeños en datasets diminutos
        # El exponente 0.8 hace que el crecimiento sea un poco más rápido que log pero menos que linear
        return math.ceil((math.log10(records + 1000) * records**0.8 * quantile) / 100)
    
    # Calcular límites base para 5 puntos de corte (20%, 40%, 60%, 80%, 95%)
    base_limits = [
        calculate_base_limit(total_records, 1.0),  # ~20% percentil
        calculate_base_limit(total_records, 2.5),  # ~40% percentil
        calculate_base_limit(total_records, 5.0),  # ~60% percentil
        calculate_base_limit(total_records, 10.0), # ~80% percentil
        calculate_base_limit(total_records, 20.0)  # ~95% percentil
    ]
    
    # Aplicar factores específicos para cada tipo de entidad
    city_limits = [max(10, round(limit * city_factor)) for limit in base_limits]
    zipcode_limits = [max(5, round(limit * zipcode_factor)) for limit in base_limits]
    broker_limits = [max(3, round(limit * broker_factor)) for limit in base_limits]
    
    # Asegurar que los límites siempre sean crecientes
    for limits in [city_limits, zipcode_limits, broker_limits]:
        for i in range(1, len(limits)):
            if limits[i] <= limits[i-1]:
                limits[i] = limits[i-1] + max(1, int(limits[i-1] * 0.2))
    
    # Detectar contexto aproximado para referencia
    if total_records < 5000:
        context = "micro"
    elif total_records < 20000:
        context = "small"
    elif total_records < 100000:
        context = "medium"
    else:
        context = "large"
    
    print(f"   🏷️ Contexto aproximado: {context} (solo referencia)")
    print(f"   🏙️ Límites para ciudades: {city_limits}")
    print(f"   📮 Límites para códigos postales: {zipcode_limits}")
    print(f"   🏢 Límites para brokers: {broker_limits}")
    
    return {
        'context': context,
        'city_limits': city_limits,
        'zipcode_limits': zipcode_limits,
        'broker_limits': broker_limits
    }

# =============================================================================
# FUNCIONES MEJORADAS CON LÍMITES TOTALMENTE DINÁMICOS
# =============================================================================

def categorize_cities_by_demand(df, city_col='city', total_records=None):
    """Categorizar ciudades por demanda con límites totalmente dinámicos"""
    print(f"\n🏙️ ANÁLISIS DE CIUDADES POR DEMANDA:")
    print("=" * 50)
    
    valid_df = df[df[city_col].notna()].copy()
    if len(valid_df) == 0:
        print("❌ No hay datos válidos para ciudades")
        return pd.DataFrame({city_col: [], 'cities_by_demand': []})
    
    cities = valid_df[city_col].value_counts().reset_index()
    cities.columns = [city_col, 'count']
    
    # ESTADÍSTICAS DETALLADAS DE LA DISTRIBUCIÓN DE CONTEOS
    print(f"   📊 Ciudades únicas: {len(cities)}")
    analyze_distribution_stats(cities['count'], 'Conteo de propiedades por ciudad')
    
    # Sugerir puntos de corte basados en percentiles
    counts = cities['count']
    suggested_cuts = [
        counts.quantile(0.2), counts.quantile(0.4), counts.quantile(0.6), 
        counts.quantile(0.8), counts.quantile(0.9), counts.quantile(0.95)
    ]
    print(f"   💡 Puntos de corte sugeridos: {[int(x) for x in suggested_cuts]}")

    # APLICAR LÍMITES DINÁMICOS SIEMPRE
    print(f"   🎯 Aplicando límites dinámicos")
    
    limits = calculate_adaptive_limits(total_records if total_records else len(df))
    city_limits = limits['city_limits']
    context = limits['context']
    
    print(f"   🎯 Usando límites calculados dinámicamente: {city_limits}")
    
    def adaptive_cities_categories(row):
        i = row['count']
        if i <= city_limits[0]:
            return 'cities_minimal_demand'
        elif i <= city_limits[1]:
            return 'cities_very_low_demand'
        elif i <= city_limits[2]:
            return 'cities_low_demand'
        elif i <= city_limits[3]:
            return 'cities_mid_demand'
        else:
            return 'cities_mega_demand'

    cities['cities_by_demand'] = cities.apply(adaptive_cities_categories, axis=1)
    
    # ANÁLISIS DE LA DISTRIBUCIÓN RESULTANTE
    category_dist = cities['cities_by_demand'].value_counts()
    print(f"\n   📋 DISTRIBUCIÓN DE CATEGORÍAS RESULTANTE:")
    for category, count in category_dist.items():
        percentage = (count / len(cities)) * 100
        print(f"      {category}: {count} ciudades ({percentage:.1f}%)")
    
    return cities[[city_col, 'cities_by_demand']]

def categorize_transactionality_by_zipcode(df, zip_col='zip_code', date_col='prev_sold_date', total_records=None):
    """Categorizar códigos postales por transaccionalidad con límites totalmente dinámicos"""
    print(f"\n📮 ANÁLISIS DE CÓDIGOS POSTALES POR TRANSACCIONALIDAD:")
    print("=" * 60)
    
    bought_streets = df[[zip_col, date_col]].copy()
    
    # Manejo robusto de fechas
    bought_streets[date_col] = pd.to_datetime(bought_streets[date_col], errors='coerce')
    
    # Filtrar datos válidos
    valid_data = bought_streets[
        bought_streets[zip_col].notna() & 
        bought_streets[date_col].notna()
    ].copy()
    
    if len(valid_data) == 0:
        print("❌ No hay datos válidos para códigos postales")
        return pd.DataFrame({zip_col: [], 'zone_by_demand': []})
    
    print(f"   📊 Registros válidos: {len(valid_data):,} de {len(df):,} totales")
    
    valid_data['sold_year'] = valid_data[date_col].dt.year
    
    grouped = valid_data.groupby(zip_col)['sold_year'].count()\
        .reset_index(name='num_prev_sales')\
        .sort_values('num_prev_sales')

    print(f"   📊 Códigos postales únicos: {len(grouped)}")
    analyze_distribution_stats(grouped['num_prev_sales'], 'Número de ventas previas por código postal')

    # APLICAR LÍMITES DINÁMICOS SIEMPRE
    print(f"   🎯 Aplicando límites dinámicos")
    
    limits = calculate_adaptive_limits(total_records if total_records else len(df))
    zipcode_limits = limits['zipcode_limits']
    context = limits['context']
    
    print(f"   🎯 Usando límites calculados dinámicamente: {zipcode_limits}")
    
    def adaptive_zipcode_categories(row):
        i = row['num_prev_sales']
        if i <= zipcode_limits[0]:
            return 'minimal_transactionality_zone'
        elif i <= zipcode_limits[1]:
            return 'low_transactionality_zone'
        elif i <= zipcode_limits[2]:
            return 'mid_transactionality_zone'
        elif i <= zipcode_limits[3]:
            return 'high_transactionality_zone'
        else:
            return 'mega_transactionality_zone'

    grouped['zone_by_demand'] = grouped.apply(adaptive_zipcode_categories, axis=1)
    
    # ANÁLISIS DE LA DISTRIBUCIÓN RESULTANTE
    category_dist = grouped['zone_by_demand'].value_counts()
    print(f"\n   📋 DISTRIBUCIÓN DE CATEGORÍAS RESULTANTE:")
    for category, count in category_dist.items():
        percentage = (count / len(grouped)) * 100
        print(f"      {category}: {count} códigos postales ({percentage:.1f}%)")
    
    return grouped[[zip_col, 'zone_by_demand']]

def categorize_brokered_by_type(df, col='brokered_by', total_records=None):
    """Categorizar brokers por tipo con límites totalmente dinámicos"""
    print(f"\n🏢 ANÁLISIS DE BROKERS POR TIPO:")
    print("=" * 40)
    
    # Filtrar valores válidos
    valid_df = df[df[col].notna() & (df[col] != '')].copy()
    if len(valid_df) == 0:
        print("❌ No hay datos válidos para brokers")
        return pd.DataFrame({col: [], 'broker_type': []})
    
    brokered = valid_df[col].value_counts().reset_index()
    brokered.columns = [col, 'count']

    print(f"   📊 Brokers únicos: {len(brokered)}")
    analyze_distribution_stats(brokered['count'], 'Número de propiedades por broker')

    # APLICAR LÍMITES DINÁMICOS SIEMPRE
    print(f"   🎯 Aplicando límites dinámicos")
    
    limits = calculate_adaptive_limits(total_records if total_records else len(df))
    broker_limits = limits['broker_limits']
    context = limits['context']
    
    print(f"   🎯 Usando límites calculados dinámicamente: {broker_limits}")
    
    def adaptive_broker_categories(row):
        i = row['count']
        if i <= broker_limits[0]:
            return 'micro_agent'
        elif i <= broker_limits[1]:
            return 'small_agent'
        elif i <= broker_limits[2]:
            return 'agent'
        elif i <= broker_limits[3]:
            return 'large_agent'
        else:
            return 'mega_corporate'

    brokered['broker_type'] = brokered.apply(adaptive_broker_categories, axis=1)
    
    # ANÁLISIS DE LA DISTRIBUCIÓN RESULTANTE
    category_dist = brokered['broker_type'].value_counts()
    print(f"\n   📋 DISTRIBUCIÓN DE CATEGORÍAS RESULTANTE:")
    for category, count in category_dist.items():
        percentage = (count / len(brokered)) * 100
        print(f"      {category}: {count} brokers ({percentage:.1f}%)")
        
    return brokered[[col, 'broker_type']]

# =============================================================================
# NUEVA FUNCIÓN: CATEGORIZACIÓN ALTERNATIVA PARA DATOS HOMOGÉNEOS
# =============================================================================

def create_alternative_categories_safe(df):
    """Crear categorías alternativas seguras basadas en variables numéricas (SIN usar price)"""
    print(f"\n🛡️ CREANDO CATEGORÍAS ALTERNATIVAS SEGURAS:")
    print("=" * 50)
    print(f"⚠️ IMPORTANTE: NO usar 'price' para crear categorías (es el target)")
    
    df_enhanced = df.copy()
    categorical_features = []
    
    # 1. Categorías de tamaño de casa (basado en house_size)
    if 'house_size' in df.columns and df['house_size'].std() > 0:
        try:
            df_enhanced['property_size_tier'] = pd.qcut(
                df['house_size'],
                q=4,
                labels=['compact', 'standard', 'spacious', 'mansion'],
                duplicates='drop'
            )
            categorical_features.append('property_size_tier')
            
            size_dist = df_enhanced['property_size_tier'].value_counts()
            print(f"   ✅ Property size tiers: {len(size_dist)} categorías")
            for tier, count in size_dist.items():
                pct = (count/len(df_enhanced))*100
                print(f"      • {tier}: {count:,} ({pct:.1f}%)")
                
        except Exception as e:
            print(f"   ⚠️ Error en property_size_tier: {str(e)}")
    
    # 2. Categorías de habitaciones (basado en bed + bath)
    if all(col in df.columns for col in ['bed', 'bath']):
        try:
            df_enhanced['total_rooms'] = df['bed'] + df['bath']
            df_enhanced['room_configuration'] = pd.cut(
                df_enhanced['total_rooms'],
                bins=[0, 3, 5, 7, 10, 100],
                labels=['minimal_rooms', 'compact_rooms', 'standard_rooms', 'spacious_rooms', 'luxury_rooms'],
                right=False
            )
            categorical_features.append('room_configuration')
            
            room_dist = df_enhanced['room_configuration'].value_counts()
            print(f"   ✅ Room configuration: {len(room_dist)} categorías")
            for config, count in room_dist.items():
                pct = (count/len(df_enhanced))*100
                print(f"      • {config}: {count:,} ({pct:.1f}%)")
                
        except Exception as e:
            print(f"   ⚠️ Error en room_configuration: {str(e)}")
    
    # 3. Categorías de lote (basado en acre_lot)
    if 'acre_lot' in df.columns and df['acre_lot'].std() > 0:
        try:
            df_enhanced['lot_size_category'] = pd.qcut(
                df['acre_lot'],
                q=3,
                labels=['small_lot', 'medium_lot', 'large_lot'],
                duplicates='drop'
            )
            categorical_features.append('lot_size_category')
            
            lot_dist = df_enhanced['lot_size_category'].value_counts()
            print(f"   ✅ Lot size categories: {len(lot_dist)} categorías")
            for category, count in lot_dist.items():
                pct = (count/len(df_enhanced))*100
                print(f"      • {category}: {count:,} ({pct:.1f}%)")
                
        except Exception as e:
            print(f"   ⚠️ Error en lot_size_category: {str(e)}")
    
    # 4. Eficiencia de espacio (basado en habitaciones/tamaño, NO precio)
    if all(col in df.columns for col in ['bed', 'bath', 'house_size']):
        try:
            df_enhanced['space_efficiency'] = (df['bed'] + df['bath']) / (df['house_size'] / 1000)
            df_enhanced['efficiency_tier'] = pd.qcut(
                df_enhanced['space_efficiency'],
                q=3,
                labels=['space_rich', 'balanced', 'space_efficient'],
                duplicates='drop'
            )
            categorical_features.append('efficiency_tier')
            
            eff_dist = df_enhanced['efficiency_tier'].value_counts()
            print(f"   ✅ Efficiency tiers: {len(eff_dist)} categorías")
            for tier, count in eff_dist.items():
                pct = (count/len(df_enhanced))*100
                print(f"      • {tier}: {count:,} ({pct:.1f}%)")
                
        except Exception as e:
            print(f"   ⚠️ Error en efficiency_tier: {str(e)}")
    
    print(f"\n   🛡️ GARANTÍA: Ninguna categoría usa 'price' (variable objetivo)")
    print(f"   📋 Variables categóricas seguras creadas: {categorical_features}")
    
    return df_enhanced[categorical_features].copy()

def detect_homogeneous_data_and_apply_strategy(df, total_records):
    """Detectar datos homogéneos y aplicar estrategia apropiada"""
    print(f"\n🔍 DETECCIÓN DE HOMOGENEIDAD Y ESTRATEGIA:")
    print("=" * 50)
    
    categorical_vars = ['city', 'zip_code', 'brokered_by', 'state']
    homogeneous_count = 0
    
    for var in categorical_vars:
        if var in df.columns:
            unique_count = df[var].nunique()
            if unique_count <= 1:
                homogeneous_count += 1
                print(f"   🚨 {var}: {unique_count} valores únicos → HOMOGÉNEO")
            else:
                print(f"   ✅ {var}: {unique_count} valores únicos → DIVERSO")
    
    print(f"\n💡 ESTRATEGIA SELECCIONADA:")
    
    if homogeneous_count >= 4:
        print(f"   🎯 TODAS LAS VARIABLES HOMOGÉNEAS → Categorización alternativa")
        return 'alternative'
    elif homogeneous_count >= 2:
        print(f"   🔧 MAYORMENTE HOMOGÉNEO → Límites dinámicos")
        return 'dynamic'
    else:
        print(f"   ✅ SUFICIENTEMENTE DIVERSO → Límites dinámicos")
        return 'dynamic'

def apply_data_processing(df):
    """Aplicar procesamiento completo a los datos con estrategia automática"""
    print(f"\n🔄 INICIANDO PROCESAMIENTO DE DATOS:")
    print("=" * 70)
    print(f"📊 Dataset inicial: {df.shape[0]:,} filas x {df.shape[1]} columnas")
    
    total_records = len(df)
    
    # ANÁLISIS INICIAL DE VARIABLES CATEGÓRICAS CLAVE
    print(f"\n📋 ANÁLISIS INICIAL DE VARIABLES CATEGÓRICAS:")
    print("=" * 50)
    
    categorical_vars = ['city', 'zip_code', 'brokered_by', 'state']
    for var in categorical_vars:
        if var in df.columns:
            analyze_distribution_stats(df[var], var)
    
    y = df['price'].copy()
    cat_cols = ['brokered_by', 'city', 'state', 'zip_code']
    num_cols = ['bed', 'bath', 'acre_lot', 'house_size']
    
    # Limpieza ROBUSTA de categóricas - manejo completo de NA
    df_clean = df.copy()
    print(f"\n🧹 TRATAMIENTO DE VALORES NA:")
    print("=" * 40)
    for col in cat_cols:
        na_before = df_clean[col].isnull().sum()
        empty_before = (df_clean[col] == '').sum() if df_clean[col].dtype == 'object' else 0
        
        # Tratamiento completo de valores faltantes/vacíos
        df_clean[col] = df_clean[col].fillna('Unknown')  # NaN → 'Unknown'
        if df_clean[col].dtype == 'object':
            df_clean[col] = df_clean[col].replace(['', ' ', 'null', 'NULL', 'nan', 'NaN', '0'], 'Unknown')
            df_clean[col] = df_clean[col].str.strip()  # Eliminar espacios
        
        na_after = (df_clean[col] == 'Unknown').sum()
        print(f"   ✅ {col}: {na_before} NaN + {empty_before} vacíos → {na_after} Unknown")
    
    # DETECTAR HOMOGENEIDAD Y APLICAR ESTRATEGIA
    strategy = detect_homogeneous_data_and_apply_strategy(df_clean, total_records)
    
    if strategy == 'alternative':
        # ESTRATEGIA: Categorización alternativa
        print(f"\n🎯 APLICANDO CATEGORIZACIÓN ALTERNATIVA:")
        df_cat = create_alternative_categories_safe(df_clean)
        df_cat['region'] = df_clean['state'].apply(get_us_region)
        
    else:
        # ESTRATEGIA: Categorización con límites dinámicos
        print(f"\n🏭 GENERANDO PARÁMETROS DE CATEGORIZACIÓN:")
        print("=" * 50)
        
        # Pasar total_records para límites dinámicos
        cities_parameters = categorize_cities_by_demand(df_clean, city_col='city', total_records=total_records)
        print(f"\n✅ Cities parameters generados: {cities_parameters.shape[0]} ciudades, {cities_parameters['cities_by_demand'].nunique()} categorías")
        
        zipcode_parameters = categorize_transactionality_by_zipcode(df_clean, zip_col='zip_code', date_col='prev_sold_date', total_records=total_records)
        print(f"\n✅ Zipcode parameters generados: {zipcode_parameters.shape[0]} códigos postales, {zipcode_parameters['zone_by_demand'].nunique() if len(zipcode_parameters) > 0 else 0} categorías")
        
        broker_parameters = categorize_brokered_by_type(df_clean, col='brokered_by', total_records=total_records)
        print(f"\n✅ Broker parameters generados: {broker_parameters.shape[0]} brokers, {broker_parameters['broker_type'].nunique() if len(broker_parameters) > 0 else 0} categorías")
        
        # Procesar categóricas
        df_cat = df_clean[cat_cols].copy()
        print(f"\n🔧 PROCESANDO VARIABLES CATEGÓRICAS:")
        print("=" * 45)
        print(f"   📊 df_cat inicial: {df_cat.shape}")
        df_cat['region'] = df_cat['state'].apply(get_us_region)
        print(f"   ✅ Después de agregar region: {df_cat.shape} - {df_cat['region'].nunique()} regiones únicas")
        
        # Merges con validación y DEBUG
        print(f"\n🔗 REALIZANDO MERGES:")
        print("=" * 30)
        df_cat = df_cat.merge(cities_parameters, how='left', on='city')
        print(f"   ✅ Merge cities completado: NaN en cities_by_demand: {df_cat['cities_by_demand'].isnull().sum()}")
        
        df_cat = df_cat.merge(zipcode_parameters, how='left', on='zip_code')
        if 'zone_by_demand' in df_cat.columns:
            print(f"   ✅ Merge zipcode completado: NaN en zone_by_demand: {df_cat['zone_by_demand'].isnull().sum()}")
        
        df_cat = df_cat.merge(broker_parameters, how='left', on='brokered_by')
        if 'broker_type' in df_cat.columns:
            print(f"   ✅ Merge broker completado: NaN en broker_type: {df_cat['broker_type'].isnull().sum()}")
        
        # Manejar NaN resultantes de merges
        for col in ['cities_by_demand', 'zone_by_demand', 'broker_type']:
            if col in df_cat.columns:
                df_cat[col] = df_cat[col].fillna('Unknown')
        
        df_cat.drop(columns=['brokered_by', 'city', 'state', 'zip_code'], inplace=True)
        print(f"   📊 Después de drop columnas: {df_cat.shape}")
        print(f"   📋 Columnas para encoding: {list(df_cat.columns)}")
    
    # ANÁLISIS FINAL ANTES DE GET_DUMMIES
    print(f"\n🎯 ANÁLISIS FINAL ANTES DE ONE-HOT ENCODING:")
    print("=" * 50)
    for col in df_cat.columns:
        unique_vals = df_cat[col].nunique()
        print(f"   📊 {col}: {unique_vals} valores únicos")
        # Mostrar top 3 más frecuentes
        top_values = df_cat[col].value_counts().head(3)
        for val, count in top_values.items():
            pct = (count / len(df_cat)) * 100
            print(f"      • {val}: {count:,} ({pct:.1f}%)")
    
    # Encoding categórico
    df_cat_encoded = pd.get_dummies(df_cat, drop_first=False).astype(int)
    print(f"\n✅ One-hot encoding completado: {df_cat_encoded.shape}")
    print(f"   📊 Columnas generadas: {len(df_cat_encoded.columns)}")
    
    # Limpiar nombres de columnas para PostgreSQL
    df_cat_encoded.columns = [col.replace('-', '_').replace(' ', '_').replace('.', '_') 
                              for col in df_cat_encoded.columns]
    
    # Procesar numéricas
    df_num = df_clean[num_cols].copy()
    df_num['rate_bath_bed'] = df_clean['bath'] / df_clean['bed'].replace(0, 1)  # Evitar división por 0
    df_num = df_num.drop(columns=['bed', 'bath'], errors='ignore')
    df_num = df_num.applymap(lambda x: np.nan if x <= 0 else x)
    df_num = np.log(df_num)
    df_num = df_num.fillna(df_num.median(numeric_only=True))
    
    # Escalado
    scaler = MinMaxScaler()
    df_num_scaled = pd.DataFrame(scaler.fit_transform(df_num), columns=df_num.columns, index=df_num.index)
    
    # Limpiar nombres de columnas numéricas
    df_num_scaled.columns = [col.replace('-', '_').replace(' ', '_').replace('.', '_') 
                             for col in df_num_scaled.columns]
    
    # Combinar resultado final
    processed_df = pd.concat([df_num_scaled, df_cat_encoded], axis=1)
    processed_df['target'] = y.values
    
    print(f"\n🎉 PROCESAMIENTO COMPLETADO:")
    print("=" * 40)
    print(f"✅ Dataset final: {len(processed_df):,} filas x {len(processed_df.columns)} columnas")
    print(f"📊 Variables numéricas: {len(df_num_scaled.columns)}")
    print(f"📊 Variables categóricas (one-hot): {len(df_cat_encoded.columns)}")
    print(f"🎯 Variable target: 1")
    print(f"🔧 Estrategia aplicada: {strategy}")
    
    return processed_df

def process_data(**context):
    """Leer datos raw, procesarlos y guardarlos como processed"""
    start_time = datetime.now()
    setup_connection()
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    batch_number = context['dag_run'].conf.get('batch_number', 1) if context['dag_run'].conf else 1
    raw_table = f"api_data_batch_{batch_number}"
    processed_table = f"api_data_batch_{batch_number}_processed"
    
    # Verificar tabla origen
    check_table_sql = f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'raw_data' 
            AND table_name = '{raw_table}'
        );
    """
    
    if not hook.get_first(check_table_sql)[0]:
        print(f"❌ Tabla raw_data.{raw_table} no existe")
        return
    
    count = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{raw_table};")[0]
    if count == 0:
        print(f"❌ Tabla raw_data.{raw_table} está vacía")
        return
    
    print(f"📥 Leyendo {count:,} registros de raw_data.{raw_table}...")
    
    # Leer datos
    select_sql = f"""
        SELECT 
            brokered_by, status, price, bed, bath, acre_lot,
            street, city, state, zip_code, house_size, prev_sold_date
        FROM raw_data.{raw_table}
        ORDER BY created_at;
    """
    
    conn_string = hook.get_uri()
    df = pd.read_sql(select_sql, conn_string)
    
    # Debug: Información del DataFrame leído
    print(f"📊 DATOS LEÍDOS:")
    print(f"   Shape: {df.shape[0]:,} filas x {df.shape[1]} columnas")
    print(f"   Columnas: {list(df.columns)}")
    print(f"   Tipos de datos: {dict(df.dtypes)}")
    
    # Aplicar procesamiento con estrategia automática
    processed_df = apply_data_processing(df)
    
    # Crear tabla procesada
    hook.run(f"DROP TABLE IF EXISTS raw_data.{processed_table} CASCADE;")
    
    columns_def = [f"{col} NUMERIC" for col in processed_df.columns]
    create_table_sql = f"""
        CREATE TABLE raw_data.{processed_table} (
            id SERIAL PRIMARY KEY,
            {', '.join(columns_def)},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    hook.run(create_table_sql)
    
    # Insertar datos usando COPY
    csv_buffer = io.StringIO()
    for _, row in processed_df.iterrows():
        values = [str(val) for val in row.values]
        csv_buffer.write('\t'.join(values) + '\n')
    
    csv_buffer.seek(0)
    
    conn = hook.get_conn()
    cursor = conn.cursor()
    
    columns_list = ', '.join(processed_df.columns)
    copy_sql = f"""
        COPY raw_data.{processed_table} ({columns_list})
        FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '')
    """
    
    cursor.copy_expert(copy_sql, csv_buffer)
    conn.commit()
    cursor.close()
    conn.close()
    
    # Métricas
    execution_time = (datetime.now() - start_time).total_seconds()
    size_mb = (len(processed_df) * len(processed_df.columns) * 8) / (1024 * 1024)
    
    print(f"\n📊 MÉTRICAS:")
    print(f"   Filas: {len(processed_df):,}")
    print(f"   Features: {len(processed_df.columns):,}")
    print(f"   Tamaño: {size_mb:.2f} MB")
    print(f"   Tiempo: {execution_time:.2f} seg")
    print(f"   Velocidad: {len(processed_df)/execution_time:,.0f} filas/seg")

def validate_processed_data(**context):
    """Validar datos procesados"""
    batch_number = context['dag_run'].conf.get('batch_number', 1) if context['dag_run'].conf else 1
    processed_table = f"api_data_batch_{batch_number}_processed"
    
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    
    count = hook.get_first(f"SELECT COUNT(*) FROM raw_data.{processed_table};")[0]
    
    if count > 0:
        columns_sql = f"""
            SELECT COUNT(*) as num_columns
            FROM information_schema.columns 
            WHERE table_schema = 'raw_data' 
            AND table_name = '{processed_table}'
            AND column_name NOT IN ('id', 'created_at');
        """
        num_columns = hook.get_first(columns_sql)[0]
        
        print(f"✅ Datos procesados exitosamente:")
        print(f"   Registros: {count:,}")
        print(f"   Features: {num_columns}")
        print(f"   Tabla: raw_data.{processed_table}")
        print(f"   Procesamiento: Límites totalmente dinámicos + Categorización inteligente")
    else:
        print("❌ No se procesaron datos")

# Tareas
process_task = PythonOperator(task_id='process_data', python_callable=process_data, dag=dag)
validate_task = PythonOperator(task_id='validate_processed_data', python_callable=validate_processed_data, dag=dag)

# Flujo
process_task >> validate_task