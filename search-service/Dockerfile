FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN for i in 1 2 3 4 5; do \
        pip install --no-cache-dir \
            --timeout=1000 \
            --retries=10 \
            -i https://mirrors.aliyun.com/pypi/simple/ \
            -r requirements.txt && break; \
        echo "pip attempt $i failed, retrying in 5s..."; \
        sleep 5; \
    done

ENV HF_HOME=/models \
    TRANSFORMERS_CACHE=/models/hub \
    SENTENCE_TRANSFORMERS_HOME=/models \
    HF_HUB_DISABLE_TELEMETRY=1 \
    PYTHONUNBUFFERED=1

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3', device='cpu')"

COPY app ./app

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]