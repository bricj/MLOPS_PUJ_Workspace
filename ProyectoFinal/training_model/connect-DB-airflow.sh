docker compose exec airflow-scheduler airflow connections add \
    --conn-type postgres \
    --conn-host 10.43.101.166 \
    --conn-login airflow \
    --conn-password airflowpass \
    --conn-port 5433 \
    --conn-schema airflow \
postgres_airflow_conn