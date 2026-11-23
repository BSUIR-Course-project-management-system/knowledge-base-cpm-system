FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

COPY migrations ./migrations

COPY alembic.ini ./

COPY scripts ./scripts
RUN sed -i 's/\r$//' ./scripts/entrypoint.sh && chmod +x ./scripts/entrypoint.sh

EXPOSE 8001

ENTRYPOINT ["./scripts/entrypoint.sh"]
