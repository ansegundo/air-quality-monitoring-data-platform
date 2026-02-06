FROM apache/airflow:2.10.3-python3.11 AS builder

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

USER airflow
WORKDIR /opt/airflow

COPY --chown=airflow:root pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry==1.8.3 && \
    poetry config virtualenvs.create false && \
    poetry install --only main,airflow --no-interaction --no-ansi --no-root

FROM apache/airflow:2.10.3-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

USER airflow
WORKDIR /opt/airflow

COPY --from=builder --chown=airflow:root /home/airflow/.local /home/airflow/.local
COPY --chown=airflow:root ./dags ./dags
COPY --chown=airflow:root ./plugins ./plugins
COPY --chown=airflow:root ./ingest ./ingest
COPY --chown=airflow:root ./api ./api

ENV PATH="/home/airflow/.local/bin:$PATH"

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl --fail http://localhost:8080/health || exit 1
