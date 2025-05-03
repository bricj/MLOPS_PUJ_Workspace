"""
DAG para validar las tablas de datos procesados de diabetes.
Este DAG asume que las tablas procesadas ya existen en la base de datos.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
import json
from typing import Dict, List, Tuple, Any, Optional

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

# Funciones de validaci�n
def validate_processed_table(table_type: str, **kwargs) -> Dict[str, Any]:
    """
    Valida los datos procesados compar�ndolos con los datos originales.
    
    Args:
        table_type: Tipo de tabla a validar ('train', 'validation' o 'test')
        
    Returns:
        Dict con los resultados de la validaci�n
    """
    ti = kwargs['ti']
    
    # Nombre de las tablas
    original_table = f"diabetes_{table_type}"
    processed_table = f"diabetes_{table_type}_processed"
    
    logger.info(f"Iniciando validaci�n de tabla {processed_table}...")
    
    # Conectar a MySQL
    mysql_hook = MySqlHook(mysql_conn_id="mysql_diabetes_conn")
    
    try:
        # 1. Validaci�n de existencia y conteo de registros
        # -------------------------------------------------
        
        # Verificar si la tabla procesada existe
        check_table_sql = f"""
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = '{processed_table}'
        """
        result = mysql_hook.get_records(check_table_sql)
        table_exists = result[0]['count'] > 0
        
        if not table_exists:
            logger.error(f"L Tabla {processed_table} no existe en la base de datos")
            return {
                'table_type': table_type,
                'exists': False,
                'validation_passed': False,
                'errors': ['Tabla procesada no existe']
            }
        
        # Contar registros en ambas tablas
        original_count_sql = f"SELECT COUNT(*) as count FROM {original_table}"
        processed_count_sql = f"SELECT COUNT(*) as count FROM {processed_table}"
        
        original_count = mysql_hook.get_records(original_count_sql)[0]['count']
        processed_count = mysql_hook.get_records(processed_count_sql)[0]['count']
        
        count_match = original_count == processed_count
        logger.info(f"Conteo de registros - Original: {original_count}, Procesado: {processed_count}")
        
        # 2. Validaci�n de la estructura de la tabla
        # -----------------------------------------
        
        # Obtener informaci�n de columnas
        column_info_sql = f"""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = '{processed_table}'
        """
        columns_info = mysql_hook.get_records(column_info_sql)
        
        # Verificar columnas esperadas
        expected_columns = ['target']  # Columna target siempre debe estar presente
        missing_columns = [col for col in expected_columns if col not in [c['COLUMN_NAME'] for c in columns_info]]
        
        # 3. Validaci�n de datos
        # ---------------------
        
        # Cargar una muestra peque�a de los datos procesados
        sample_sql = f"SELECT * FROM {processed_table} LIMIT 100"
        df_processed = mysql_hook.get_pandas_df(sample_sql)
        
        # Verificar que no hay valores nulos en columnas cr�ticas
        critical_columns = ['target']
        null_critical = any(df_processed[col].isnull().any() for col in critical_columns if col in df_processed.columns)
        
        # Verificar que los valores de target son v�lidos
        if 'target' in df_processed.columns:
            target_values = df_processed['target'].unique()
            valid_target_values = set(['YES', 'NO'])
            invalid_targets = set(target_values) - valid_target_values
            target_valid = len(invalid_targets) == 0
        else:
            target_valid = False
            invalid_targets = ["Columna 'target' no encontrada"]
        
        # 4. Validaci�n del balance de clases
        # ----------------------------------
        
        # Solo para conjuntos de entrenamiento
        class_balance_info = {}
        if table_type == 'train' and 'target' in df_processed.columns:
            class_counts = df_processed['target'].value_counts().to_dict()
            class_balance_info = {
                'class_counts': class_counts,
                'class_ratio': class_counts.get('YES', 0) / max(1, class_counts.get('NO', 1))
            }
        
        # 5. Validaci�n de transformaciones
        # --------------------------------
        
        # Verificar que hay columnas num�ricas (resultado del OneHotEncoder)
        numeric_columns = df_processed.select_dtypes(include=[np.number]).columns.tolist()
        has_numeric_features = len(numeric_columns) > 0
        
        # Compilar resultados de la validaci�n
        errors = []
        warnings = []
        
        if not count_match:
            errors.append(f"Conteo de registros no coincide: Original={original_count}, Procesado={processed_count}")
        
        if missing_columns:
            errors.append(f"Columnas esperadas faltantes: {missing_columns}")
        
        if null_critical:
            errors.append("Hay valores nulos en columnas cr�ticas")
        
        if not target_valid:
            errors.append(f"Valores inv�lidos en columna 'target': {invalid_targets}")
        
        if not has_numeric_features:
            warnings.append("No se encontraron columnas num�ricas, posible error en la transformaci�n")
        
        # Resultado final
        validation_result = {
            'table_type': table_type,
            'exists': True,
            'validation_passed': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'row_count': {
                'original': original_count,
                'processed': processed_count,
                'match': count_match
            },
            'columns_info': {
                'total': len(columns_info),
                'missing_expected': missing_columns
            }
        }
        
        if class_balance_info:
            validation_result['class_balance'] = class_balance_info
        
        # Guardar resultado en XCom
        validation_result_json = json.dumps(validation_result)
        kwargs['ti'].xcom_push(key=f'{table_type}_validation_result', value=validation_result_json)
        
        # Registrar resultado
        if validation_result['validation_passed']:
            logger.info(f" Validaci�n de {processed_table} exitosa")
        else:
            logger.warning(f"� Validaci�n de {processed_table} fall� con errores: {errors}")
            if warnings:
                logger.warning(f"� Advertencias: {warnings}")
        
        return validation_result
    
    except Exception as e:
        logger.error(f"L Error durante la validaci�n de {processed_table}: {str(e)}")
        # Guardar error en XCom
        error_result = {
            'table_type': table_type,
            'exists': table_exists if 'table_exists' in locals() else False,
            'validation_passed': False,
            'errors': [str(e)]
        }
        kwargs['ti'].xcom_push(key=f'{table_type}_validation_result', value=json.dumps(error_result))
        raise

def perform_data_quality_checks(table_type: str, **kwargs) -> Dict[str, Any]:
    """
    Realiza verificaciones de calidad de datos m�s profundas en los datos procesados.
    
    Args:
        table_type: Tipo de tabla a validar ('train', 'validation' o 'test')
        
    Returns:
        Dict con los resultados de las verificaciones
    """
    ti = kwargs['ti']
    
    # Nombre de la tabla procesada
    processed_table = f"diabetes_{table_type}_processed"
    
    logger.info(f"Iniciando verificaciones de calidad para {processed_table}...")
    
    # Conectar a MySQL
    mysql_hook = MySqlHook(mysql_conn_id="mysql_diabetes_conn")
    
    try:
        # Cargar todos los datos procesados
        df_processed = mysql_hook.get_pandas_df(f"SELECT * FROM {processed_table}")
        
        # 1. An�lisis estad�stico b�sico
        # -----------------------------
        
        # Calcular estad�sticas para columnas num�ricas
        numeric_cols = df_processed.select_dtypes(include=[np.number]).columns
        stats = {}
        
        if len(numeric_cols) > 0:
            # Excluir columnas de ID para las estad�sticas
            num_cols_for_stats = [col for col in numeric_cols if not (col.endswith('_id') or col == 'encounter_id' or col == 'patient_nbr')]
            
            if num_cols_for_stats:
                # Calcular estad�sticas b�sicas
                df_stats = df_processed[num_cols_for_stats].describe().transpose()
                
                # Convertir a diccionario para almacenar en XCom
                stats = df_stats.to_dict()
                
                # Verificar valores at�picos (outliers)
                outliers = {}
                for col in num_cols_for_stats:
                    Q1 = df_processed[col].quantile(0.25)
                    Q3 = df_processed[col].quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR
                    
                    outlier_count = ((df_processed[col] < lower_bound) | (df_processed[col] > upper_bound)).sum()
                    outlier_percent = (outlier_count / len(df_processed)) * 100
                    
                    outliers[col] = {
                        'count': int(outlier_count),
                        'percent': float(outlier_percent)
                    }
        
        # 2. Verificar distribuci�n de clases si es un problema de clasificaci�n
        # -------------------------------------------------------------------
        
        class_distribution = None
        if 'target' in df_processed.columns:
            class_distribution = df_processed['target'].value_counts(normalize=True).to_dict()
            
            # Verificar si hay desbalance extremo
            min_class_pct = min(class_distribution.values())
            is_imbalanced = min_class_pct < 0.10  # menos del 10% en alguna clase
        
        # 3. Verificar correlaciones entre caracter�sticas y target
        # ------------------------------------------------------
        
        correlations = None
        if 'target' in df_processed.columns and len(numeric_cols) > 0:
            # Convertir target a num�rico temporalmente para correlaci�n
            if df_processed['target'].dtype == 'object':
                target_numeric = df_processed['target'].map({'YES': 1, 'NO': 0})
            else:
                target_numeric = df_processed['target']
            
            # Calcular correlaci�n con cada caracter�stica num�rica
            corr_with_target = {}
            for col in num_cols_for_stats:
                corr = df_processed[col].corr(target_numeric)
                if not np.isnan(corr):
                    corr_with_target[col] = float(corr)
            
            # Ordenar por valor absoluto de correlaci�n
            correlations = {k: v for k, v in sorted(
                corr_with_target.items(), 
                key=lambda item: abs(item[1]), 
                reverse=True
            )}
        
        # 4. Verificar que las transformaciones se aplicaron correctamente
        # --------------------------------------------------------------
        
        # Verificar rangos esperados para datos escalados (deber�an estar cerca de media 0 y desv. est�ndar 1)
        transformation_check = {}
        if len(num_cols_for_stats) > 0:
            for col in num_cols_for_stats:
                mean = df_processed[col].mean()
                std = df_processed[col].std()
                
                # Si la columna est� escalada, mean deber�a estar cerca de 0 y std cerca de 1
                is_likely_scaled = abs(mean) < 0.5 and 0.5 < std < 1.5
                
                transformation_check[col] = {
                    'mean': float(mean),
                    'std': float(std),
                    'likely_scaled': is_likely_scaled
                }
        
        # Verificar one-hot encoding (buscar columnas categ�ricas en los datos originales)
        categorical_encoding_check = {}
        original_categorical_cols = ['race', 'gender', 'age', 'admission_type_id', 'discharge_disposition_id', 
                                    'admission_source_id', 'diag_1']
        
        # Buscar patrones de columnas one-hot codificadas
        for base_col in original_categorical_cols:
            matching_cols = [col for col in df_processed.columns if col.startswith(f"{base_col}_")]
            if matching_cols:
                categorical_encoding_check[base_col] = {
                    'encoded_columns_count': len(matching_cols),
                    'encoded_column_examples': matching_cols[:3] if len(matching_cols) > 3 else matching_cols
                }
        
        # Compilar resultados
        quality_result = {
            'table_type': table_type,
            'row_count': len(df_processed),
            'column_count': len(df_processed.columns),
            'has_target_column': 'target' in df_processed.columns
        }
        
        if stats:
            quality_result['statistics'] = stats
            quality_result['outliers'] = outliers
        
        if class_distribution:
            quality_result['class_distribution'] = class_distribution
            quality_result['is_imbalanced'] = is_imbalanced if 'is_imbalanced' in locals() else None
        
        if correlations:
            quality_result['correlations_with_target'] = correlations
        
        if transformation_check:
            quality_result['transformation_check'] = transformation_check
        
        if categorical_encoding_check:
            quality_result['categorical_encoding'] = categorical_encoding_check
        
        # Identificar posibles problemas
        warnings = []
        
        if 'is_imbalanced' in locals() and is_imbalanced:
            warnings.append(f"Desbalance significativo de clases detectado: {class_distribution}")
        
        if outliers:
            high_outlier_cols = {col: info for col, info in outliers.items() if info['percent'] > 5}
            if high_outlier_cols:
                warnings.append(f"Alto porcentaje de valores at�picos en columnas: {list(high_outlier_cols.keys())}")
        
        if transformation_check:
            poorly_scaled = [col for col, check in transformation_check.items() 
                           if not check['likely_scaled'] and 'service_utilization' not in col]
            
            if poorly_scaled:
                warnings.append(f"Posible problema con escalado en columnas: {poorly_scaled}")
        
        quality_result['warnings'] = warnings
        quality_result['quality_passed'] = len(warnings) == 0
        
        # Guardar resultado en XCom
        quality_result_json = json.dumps(quality_result, default=str)  # default=str maneja tipos no serializables
        kwargs['ti'].xcom_push(key=f'{table_type}_quality_result', value=quality_result_json)
        
        # Registrar resultado
        if quality_result['quality_passed']:
            logger.info(f" Verificaci�n de calidad para {processed_table} exitosa")
        else:
            logger.warning(f"� Verificaci�n de calidad para {processed_table} encontr� advertencias: {warnings}")
        
        return quality_result
    
    except Exception as e:
        logger.error(f"L Error durante verificaci�n de calidad para {processed_table}: {str(e)}")
        error_result = {
            'table_type': table_type,
            'quality_passed': False,
            'errors': [str(e)]
        }
        kwargs['ti'].xcom_push(key=f'{table_type}_quality_result', value=json.dumps(error_result, default=str))
        raise

def compare_data_distributions(table_type: str, reference_type: str = 'train', **kwargs) -> Dict[str, Any]:
    """
    Compara las distribuciones de datos entre dos tablas procesadas.
    �til para verificar que validation y test tienen distribuciones similares a train.
    
    Args:
        table_type: Tipo de tabla a comparar ('validation' o 'test')
        reference_type: Tabla de referencia (por defecto 'train')
        
    Returns:
        Dict con los resultados de la comparaci�n
    """
    if table_type == reference_type:
        logger.info(f"Saltando comparaci�n para {table_type} ya que es la misma que la referencia")
        return {'skipped': True, 'reason': 'Same as reference'}
    
    ti = kwargs['ti']
    
    # Nombres de las tablas
    table = f"diabetes_{table_type}_processed"
    reference = f"diabetes_{reference_type}_processed"
    
    logger.info(f"Iniciando comparaci�n de distribuciones entre {table} y {reference}...")
    
    # Conectar a MySQL
    mysql_hook = MySqlHook(mysql_conn_id="mysql_diabetes_conn")
    
    try:
        # Cargar datos de ambas tablas (muestras para tablas grandes)
        # Ajusta el l�mite seg�n el tama�o de tus datos
        sample_limit = 1000
        table_df = mysql_hook.get_pandas_df(f"SELECT * FROM {table} LIMIT {sample_limit}")
        reference_df = mysql_hook.get_pandas_df(f"SELECT * FROM {reference} LIMIT {sample_limit}")
        
        # Verificar columnas comunes
        common_columns = list(set(table_df.columns) & set(reference_df.columns))
        numeric_cols = [col for col in common_columns if np.issubdtype(table_df[col].dtype, np.number) and 
                        np.issubdtype(reference_df[col].dtype, np.number)]
        
        # Excluir columnas de ID
        numeric_cols = [col for col in numeric_cols if not (col.endswith('_id') or col == 'encounter_id' or col == 'patient_nbr')]
        
        # 1. Comparar estad�sticas b�sicas
        # -------------------------------
        stats_comparison = {}
        for col in numeric_cols:
            table_mean = table_df[col].mean()
            reference_mean = reference_df[col].mean()
            mean_diff_percent = abs((table_mean - reference_mean) / (reference_mean if reference_mean != 0 else 1)) * 100
            
            table_std = table_df[col].std()
            reference_std = reference_df[col].std()
            std_diff_percent = abs((table_std - reference_std) / (reference_std if reference_std != 0 else 1)) * 100
            
            stats_comparison[col] = {
                'mean_difference_percent': float(mean_diff_percent),
                'std_difference_percent': float(std_diff_percent),
                'significant_difference': mean_diff_percent > 10 or std_diff_percent > 20
            }
        
        # 2. Comparar distribuci�n de clases si es un problema de clasificaci�n
        # ------------------------------------------------------------------
        class_comparison = None
        if 'target' in common_columns:
            table_dist = table_df['target'].value_counts(normalize=True).to_dict()
            reference_dist = reference_df['target'].value_counts(normalize=True).to_dict()
            
            # Calcular diferencia en cada clase
            class_diffs = {}
            for cls in set(table_dist.keys()) | set(reference_dist.keys()):
                table_pct = table_dist.get(cls, 0) * 100
                reference_pct = reference_dist.get(cls, 0) * 100
                abs_diff = abs(table_pct - reference_pct)
                
                class_diffs[cls] = {
                    'table_percent': float(table_pct),
                    'reference_percent': float(reference_pct),
                    'absolute_diff_percent': float(abs_diff),
                    'significant_difference': abs_diff > 5  # diferencia de m�s del 5%
                }
            
            class_comparison = {
                'table_distribution': table_dist,
                'reference_distribution': reference_dist,
                'class_differences': class_diffs
            }
        
        # Compilar resultados
        comparison_result = {
            'table_type': table_type,
            'reference_type': reference_type,
            'common_numeric_columns': numeric_cols,
            'statistics_comparison': stats_comparison
        }
        
        if class_comparison:
            comparison_result['class_comparison'] = class_comparison
        
        # Identificar posibles problemas en la comparaci�n
        warnings = []
        
        # Advertencias para diferencias estad�sticas
        significant_diff_cols = [col for col, stats in stats_comparison.items() if stats['significant_difference']]
        if significant_diff_cols:
            warnings.append(f"Diferencias estad�sticas significativas en columnas: {significant_diff_cols}")
        
        # Advertencias para diferencias en distribuci�n de clases
        if class_comparison:
            significant_class_diffs = [cls for cls, diff in class_comparison['class_differences'].items() 
                                     if diff['significant_difference']]
            if significant_class_diffs:
                warnings.append(f"Diferencias significativas en distribuci�n de clases: {significant_class_diffs}")
        
        comparison_result['warnings'] = warnings
        comparison_result['comparison_passed'] = len(warnings) == 0
        
        # Guardar resultado en XCom
        comparison_result_json = json.dumps(comparison_result, default=str)
        kwargs['ti'].xcom_push(key=f'{table_type}_comparison_result', value=comparison_result_json)
        
        # Registrar resultado
        if comparison_result['comparison_passed']:
            logger.info(f" Comparaci�n entre {table} y {reference} exitosa")
        else:
            logger.warning(f"� Comparaci�n entre {table} y {reference} encontr� diferencias: {warnings}")
        
        return comparison_result
    
    except Exception as e:
        logger.error(f"L Error durante comparaci�n de {table} con {reference}: {str(e)}")
        error_result = {
            'table_type': table_type,
            'reference_type': reference_type,
            'comparison_passed': False,
            'errors': [str(e)]
        }
        kwargs['ti'].xcom_push(key=f'{table_type}_comparison_result', value=json.dumps(error_result, default=str))
        raise

def generate_validation_report(**kwargs) -> None:
    """
    Genera un informe completo de validaci�n basado en todos los resultados anteriores.
    """
    ti = kwargs['ti']
    
    # Tipos de tablas que hemos procesado
    tables = ['train', 'validation', 'test']
    
    logger.info("Generando informe de validaci�n completo...")
    
    # Recopilar resultados de validaci�n
    validation_results = {}
    quality_results = {}
    comparison_results = {}
    
    for table in tables:
        # Obtener resultados de validaci�n b�sica
        validation_json = ti.xcom_pull(key=f'{table}_validation_result', task_ids=f'validate_{table}_data')
        if validation_json:
            try:
                validation_results[table] = json.loads(validation_json)
            except:
                validation_results[table] = {'error': 'No se pudo parsear el resultado de validaci�n'}
        
        # Obtener resultados de calidad
        quality_json = ti.xcom_pull(key=f'{table}_quality_result', task_ids=f'check_{table}_quality')
        if quality_json:
            try:
                quality_results[table] = json.loads(quality_json)
            except:
                quality_results[table] = {'error': 'No se pudo parsear el resultado de calidad'}
        
        # Obtener resultados de comparaci�n (solo para validation y test)
        if table != 'train':
            comparison_json = ti.xcom_pull(key=f'{table}_comparison_result', task_ids=f'compare_{table}_distribution')
            if comparison_json:
                try:
                    comparison_results[table] = json.loads(comparison_json)
                except:
                    comparison_results[table] = {'error': 'No se pudo parsear el resultado de comparaci�n'}
    
    # Resumir estado general
    all_validations_passed = all(
        res.get('validation_passed', False) 
        for res in validation_results.values() if isinstance(res, dict)
    )
    
    all_quality_passed = all(
        res.get('quality_passed', False)
        for res in quality_results.values() if isinstance(res, dict)
    )
    
    all_comparisons_passed = all(
        res.get('comparison_passed', False)
        for res in comparison_results.values() if isinstance(res, dict)
    )
    
    overall_status = all_validations_passed and all_quality_passed and all_comparisons_passed
    
    # Compilar informe completo
    report = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'overall_status': 'PASS' if overall_status else 'FAIL',
        'validation_summary': {
            'all_validations_passed': all_validations_passed,
            'all_quality_passed': all_quality_passed,
            'all_comparisons_passed': all_comparisons_passed
        },
        'validation_results': validation_results,
        'quality_results': quality_results,
        'comparison_results': comparison_results
    }
    
    # Resumen de problemas encontrados
    all_warnings = []
    all_errors = []
    
    # Recopilar advertencias y errores
    for table, res in validation_results.items():
        if isinstance(res, dict):
            if 'errors' in res and res['errors']:
                all_errors.extend([f"{table}: {err}" for err in res['errors']])
            if 'warnings' in res and res['warnings']:
                all_warnings.extend([f"{table}: {warn}" for warn in res['warnings']])
    
    for table, res in quality_results.items():
        if isinstance(res, dict) and 'warnings' in res and res['warnings']:
            all_warnings.extend([f"{table} (quality): {warn}" for warn in res['warnings']])
    
    for table, res in comparison_results.items():
        if isinstance(res, dict) and 'warnings' in res and res['warnings']:
            all_warnings.extend([f"{table} (comparison): {warn}" for warn in res['warnings']])
    
    report['all_errors'] = all_errors
    report['all_warnings'] = all_warnings
    
    # Guardar informe completo en XCom
    report_json = json.dumps(report, default=str)
    kwargs['ti'].xcom_push(key='validation_report', value=report_json)
    
    # Registrar resultados
    logger.info("=== INFORME DE VALIDACI�N ===")
    logger.info(f"Estado general: {' PASS' if overall_status else 'L FAIL'}")
    
    if all_errors:
        logger.error("Errores encontrados:")
        for err in all_errors:
            logger.error(f"  - {err}")
    
    if all_warnings:
        logger.warning("Advertencias encontradas:")
        for warn in all_warnings:
            logger.warning(f"  - {warn}")
    
    logger.info("Validaci�n de datos completada.")
    
    return report

# Definici�n del DAG
with DAG(
    'validate_diabetes_processed_tables',
    default_args=default_args,
    description='Valida las tablas de datos procesados de diabetes',
    schedule_interval=None,  # Ejecuci�n manual
) as dag:
    
    # TAREAS DE VALIDACI�N
    # -----------------
    
    # Tareas para validar datos procesados
    validate_train = PythonOperator(
        task_id='validate_train_data',
        python_callable=validate_processed_table,
        op_kwargs={'table_type': 'train'},
        provide_context=True,
    )
    
    validate_validation = PythonOperator(
        task_id='validate_validation_data',
        python_callable=validate_processed_table,
        op_kwargs={'table_type': 'validation'},
        provide_context=True,
    )
    
    validate_test = PythonOperator(
        task_id='validate_test_data',
        python_callable=validate_processed_table,
        op_kwargs={'table_type': 'test'},
        provide_context=True,
    )
    
    # Tareas para verificar calidad de datos
    check_train_quality = PythonOperator(
        task_id='check_train_quality',
        python_callable=perform_data_quality_checks,
        op_kwargs={'table_type': 'train'},
        provide_context=True,
    )
    
    check_validation_quality = PythonOperator(
        task_id='check_validation_quality',
        python_callable=perform_data_quality_checks,
        op_kwargs={'table_type': 'validation'},
        provide_context=True,
    )
    
    check_test_quality = PythonOperator(
        task_id='check_test_quality',
        python_callable=perform_data_quality_checks,
        op_kwargs={'table_type': 'test'},
        provide_context=True,
    )
    
    # Tareas para comparar distribuciones
    compare_validation = PythonOperator(
        task_id='compare_validation_distribution',
        python_callable=compare_data_distributions,
        op_kwargs={'table_type': 'validation', 'reference_type': 'train'},
        provide_context=True,
    )
    
    compare_test = PythonOperator(
        task_id='compare_test_distribution',
        python_callable=compare_data_distributions,
        op_kwargs={'table_type': 'test', 'reference_type': 'train'},
        provide_context=True,
    )
    
    # Tarea para generar informe final de validaci�n
    validation_report = PythonOperator(
        task_id='generate_validation_report',
        python_callable=generate_validation_report,
        provide_context=True,
    )
    
    # Definir el flujo de ejecuci�n
    
    # Primero ejecutar las validaciones b�sicas en paralelo
    [validate_train, validate_validation, validate_test]
    
    # Luego verificar la calidad de los datos (depende de la validaci�n b�sica)
    validate_train >> check_train_quality
    validate_validation >> check_validation_quality
    validate_test >> check_test_quality
    
    # Comparar distribuciones (dependencia de los chequeos de calidad)
    [check_validation_quality, check_train_quality] >> compare_validation
    [check_test_quality, check_train_quality] >> compare_test
    
    # Generar informe final despu�s de todas las validaciones
    [check_train_quality, compare_validation, compare_test] >> validation_report