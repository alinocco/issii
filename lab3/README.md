# Лабораторная работа 3: Деплой модели тревожности

Продолжение [lab2](../lab2/README.md): экспорт обученной sklearn-модели, сервинг через **BentoML** (REST), потоковая обработка через **Apache Kafka**, мониторинг **Prometheus/Grafana**, нагрузочное тестирование **Locust**.

**Полная пошаговая инструкция:** [DEPLOYMENT.md](DEPLOYMENT.md)

## Быстрый старт (Docker)

```bash
cd lab3
docker compose up --build -d
```

| Сервис        | URL                          |
|---------------|------------------------------|
| REST API      | http://localhost:3000        |
| Prometheus    | http://localhost:9090        |
| Grafana       | http://localhost:3001 (admin/admin) |
| Kafka (`dhi.io/kafka:4.2-native`) | localhost:9092 |

Проверка REST:

```bash
curl -s -X POST http://localhost:3000/predict \
  -H 'Content-Type: application/json' \
  -d '{"features":{"anxiety_score":0.7,"stress_score":0.6,"sleep_quality_score":0.3,"support_score":0.4,"insomnia_score":0.5}}'
```

## Локальная разработка

```bash
cd lab3
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Данные: lab2 parquet или синтетика
export LOCAL_DATA_PATH="$(pwd)/data/sample_anxiety.parquet"
python scripts/generate_sample_data.py
python -m src.export_model --model logistic

# REST (BentoML)
export BENTOML_HOME="$(pwd)/.bentoml"
export ARTIFACT_PATH="$(pwd)/artifacts/logistic"
bentoml serve service:AnxietyService --port 3000

# Kafka (нужен брокер)
docker compose up -d kafka
python -m src.kafka_consumer &
python -m src.kafka_producer --limit 500

# Нагрузочный тест
chmod +x scripts/run_load_test.sh
./scripts/run_load_test.sh
```

## Структура

```
lab3/
  src/export_model.py      # обучение + ONNX/joblib
  src/onnx_runtime.py      # импорт ONNX
  service.py               # BentoML REST
  src/kafka_*.py           # producer/consumer
  load_test/locustfile.py
  monitoring/              # Prometheus + Grafana
  report/report.md         # отчёт с анализом
```

Подробный анализ форматов экспорта, архитектуры и результатов — в [report/report.md](report/report.md).
