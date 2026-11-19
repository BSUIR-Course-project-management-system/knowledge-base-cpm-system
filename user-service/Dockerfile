FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

COPY migrations ./migrations

COPY alembic.ini ./

COPY scripts ./scripts
RUN sed -i 's/\r$//' ./scripts/entrypoint.sh && chmod +x ./scripts/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./scripts/entrypoint.sh"]
