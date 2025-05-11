docker compose exec airflow-scheduler airflow connections add \
    --conn-type postgres \
    --conn-host 10.43.101.168 \
    --conn-login airflow \
    --conn-password airflowpass \
    --conn-port 32148 \
    --conn-schema airflow \
postgres_airflow_conn