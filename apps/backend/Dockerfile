FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e . && \
    chmod +x /app/docker-entrypoint.sh

RUN useradd -m -u 10001 appuser
RUN mkdir -p /var/lib/homelab && chown -R appuser:appuser /var/lib/homelab /app

USER appuser

EXPOSE 8000

CMD ["./docker-entrypoint.sh"]
