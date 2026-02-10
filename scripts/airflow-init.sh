#! /usr/bin/env bash
set -euo pipefail

POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_USER="${POSTGRES_USER:-airflow}"
POSTGRES_DB="${POSTGRES_DB:-airflow}"

AIRFLOW_ADMIN_USERNAME="${AIRFLOW_ADMIN_USERNAME:-admin}"
AIRFLOW_ADMIN_PASSWORD="${AIRFLOW_ADMIN_PASSWORD:-admin}"
AIRFLOW_ADMIN_EMAIL="${AIRFLOW_ADMIN_EMAIL:-admin@localhost}"

echo "Waiting for Postgres at ${POSTGRES_HOST}..."
until pg_isready -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"; do
    sleep 2
done

echo "Applying Airflow DB migrations..."
airflow db upgrade

if ! airflow users list | awk '{print $2}' | grep -xq "${AIRFLOW_ADMIN_USERNAME}"; then
    echo "Creating admin user..."
    airflow users create \
        --username "${AIRFLOW_ADMIN_USERNAME}" \
        --password "${AIRFLOW_ADMIN_PASSWORD}" \
        --firstname Admin \
        --lastname User \
        --role Admin \
        --email "${AIRFLOW_ADMIN_EMAIL}"
else
    echo "Admin user already exists."
fi

echo "Airflow init complete."
    
