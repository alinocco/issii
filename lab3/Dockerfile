FROM python:3.11-slim

WORKDIR /app
ENV BENTOML_HOME=/app/.bentoml

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Синтетические данные + экспорт модели при сборке (для демо без MinIO)
ENV LOCAL_DATA_PATH=/app/data/sample_anxiety.parquet
RUN python scripts/generate_sample_data.py && python -m src.export_model --model logistic

EXPOSE 3000 9091

CMD ["bentoml", "serve", "service:AnxietyService", "--host", "0.0.0.0", "--port", "3000"]
