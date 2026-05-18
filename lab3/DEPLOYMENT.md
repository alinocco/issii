# Инструкция по развёртыванию и запуску (lab3)

## Что поднимается

| Компонент | Назначение | Порт (хост) |
|-----------|------------|-------------|
| **bentoml-api** | REST API, инференс ONNX | 3000 |
| **bentoml-api** (metrics) | Метрики Prometheus | 9091 |
| **kafka** | Брокер сообщений | 9092 |
| **kafka-worker** | Consumer: читает признаки → предсказания | 9102 (metrics) |
| **kafka-init** | Однократная заливка 2000 сообщений в Kafka | — |
| **prometheus** | Сбор метрик | 9090 |
| **grafana** | Дашборды | 3001 |

---

## Вариант A: всё в Docker (рекомендуется)

### Требования

- Docker и Docker Compose v2
- Образ Kafka: **`dhi.io/kafka:4.2-native`** (уже скачан локально или `docker pull dhi.io/kafka:4.2-native`; при необходимости `docker login dhi.io`)
- ~4 GB свободной RAM
- Порты **3000, 3001, 9090, 9091, 9092, 9102** свободны

### 1. Запуск стека

```bash
cd /home/yomma/itmo/issii/lab3
docker compose up --build -d
```

Первый запуск занимает **5–15 минут** (сборка образов, установка зависимостей, обучение и экспорт модели внутри образа).

### 2. Проверить статус контейнеров

```bash
docker compose ps
```

Ожидаемо: `kafka`, `bentoml-api`, `kafka-worker`, `prometheus`, `grafana` — **Up**.  
`kafka-init` — **Exited (0)** после отправки сообщений (это нормально).

Логи при проблемах:

```bash
docker compose logs -f bentoml-api
docker compose logs -f kafka-worker
docker compose logs kafka-init
```

### 3. Проверить REST API

```bash
curl -s -X POST http://localhost:3000/health \
  -H 'Content-Type: application/json' \
  -d '{}'
```

```bash
curl -s -X POST http://localhost:3000/predict \
  -H 'Content-Type: application/json' \
  -d '{"features":{"anxiety_score":0.7,"stress_score":0.6,"sleep_quality_score":0.3,"support_score":0.4,"insomnia_score":0.5}}'
```

Ожидаемый ответ `/predict`:

```json
{"prediction": 1, "probability_high_anxiety": 0.98, "model_format": "onnx"}
```

Имена признаков должны совпадать с `artifacts/logistic/model_meta.json` (в Docker они зашиты при сборке).

### 4. Prometheus

Открыть в браузере: **http://localhost:9090**

Полезные запросы (вкладка Graph → Execute):

```promql
sum(rate(anxiety_predictions_total[1m])) by (source, status)
histogram_quantile(0.95, sum(rate(anxiety_prediction_latency_seconds_bucket[1m])) by (le, source))
```

Проверка targets: **Status → Targets** — должны быть `bentoml-api:9091` и `kafka-worker:9092` в состоянии **UP**.

### 5. Grafana

- URL: **http://localhost:3001**
- Логин: `admin` / пароль: `admin`
- Дашборд: **Dashboards → Lab3 → Anxiety Model Serving**

Если графики пустые — подождите 1–2 минуты после нагрузки или перезапустите producer (см. ниже).

### 6. Kafka-пайплайн

При `docker compose up` сервис **kafka-init** автоматически публикует 2000 записей в топик `anxiety.features`. Worker пишет ответы в `anxiety.predictions`.

Повторная заливка вручную:

```bash
docker compose run --rm kafka-init
```

Просмотр метрик worker: **http://localhost:9102/metrics**

### 7. Нагрузочный тест (с хоста)

```bash
cd /home/yomma/itmo/issii/lab3
python3 -m venv .venv && source .venv/bin/activate
pip install locust requests
mkdir -p reports
locust -f load_test/locustfile.py \
  --host http://localhost:3000 \
  --headless -u 50 -r 10 -t 60s \
  --html reports/locust_report.html \
  --csv reports/locust
```

Отчёт: `reports/locust_report.html`. Во время теста смотрите Grafana (RPS, latency).

### 8. Остановка

```bash
docker compose down
# с удалением volumes (если нужно с нуля):
# docker compose down -v
```

---

## Вариант B: локально (без полного Docker)

Удобно для отладки кода. Kafka и мониторинг можно поднять выборочно через Docker.

### 1. Окружение Python

```bash
cd /home/yomma/itmo/issii/lab3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Данные и экспорт модели

**Синтетика (быстро, без lab1/lab2):**

```bash
python scripts/generate_sample_data.py
export LOCAL_DATA_PATH="$(pwd)/data/sample_anxiety.parquet"
python -m src.export_model --model logistic
```

**Реальные данные из lab2:**

```bash
export LOCAL_DATA_PATH="/путь/к/final_anxiety_dataset.parquet"
python -m src.export_model --model logistic
```

или MinIO (если запущен из lab1):

```bash
export MINIO_ENDPOINT=http://localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin
export MINIO_BUCKET=mental-health-lake
export FEATURES_KEY=processed/final_anxiety_dataset.parquet
python -m src.export_model --model logistic
```

Артефакты появятся в `artifacts/logistic/`:
- `model.onnx` — для инференса
- `model.joblib` — sklearn (отладка)
- `model_meta.json` — список признаков

### 3. REST API (BentoML)

В **отдельном терминале**:

```bash
cd /home/yomma/itmo/issii/lab3
source .venv/bin/activate
export BENTOML_HOME="$(pwd)/.bentoml"
export ARTIFACT_PATH="$(pwd)/artifacts/logistic"
bentoml serve service:AnxietyService --port 3000
```

Метрики: **http://localhost:9091/metrics**

### 4. Kafka (только брокер в Docker)

```bash
docker compose up -d kafka
# дождаться healthy:
docker compose ps kafka
```

В **двух терминалах** (с активированным venv):

```bash
# Терминал 1 — consumer
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
python -m src.kafka_consumer
```

```bash
# Терминал 2 — producer
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export LOCAL_DATA_PATH="$(pwd)/data/sample_anxiety.parquet"
python -m src.kafka_producer --limit 500
```

### 5. Prometheus + Grafana локально

```bash
docker compose up -d prometheus grafana
```

(Нужен запущенный `bentoml-api` или локальный BentoML на портах 9091/9092 — при чисто локальном запуске поправьте `monitoring/prometheus.yml`, заменив `bentoml-api` на `host.docker.internal:9091`.)

### 6. Нагрузочный тест

```bash
chmod +x scripts/run_load_test.sh
./scripts/run_load_test.sh
```

Или с UI Locust: `locust -f load_test/locustfile.py --host http://localhost:3000` → **http://localhost:8089**

---

## Куда смотреть при сдаче / демонстрации

| Что показать | Где |
|--------------|-----|
| Работа REST | `curl` на `/predict` или Locust-отчёт |
| Экспорт ONNX | `artifacts/logistic/model.onnx` |
| Kafka как источник | логи `kafka-worker`, метрики `source="kafka"` в Prometheus |
| Мониторинг | Grafana дашборд + Prometheus targets |
| Анализ | `report/report.md` |

---

## Частые проблемы

| Симптом | Решение |
|---------|---------|
| `Permission denied: bentoml` | `export BENTOML_HOME="$(pwd)/.bentoml"` |
| `KeyError` / ошибка признаков в `/predict` | Сверить JSON с `artifacts/logistic/model_meta.json` |
| Порт 3000 занят | Остановить другой процесс или сменить порт в `bentoml serve --port 3001` |
| Grafana пустая | Сгенерировать нагрузку (Locust или `kafka-init`) |
| `kafka-init` failed | `docker compose logs kafka-init`; убедиться что Kafka healthy |
| `dhi.io/kafka` not found | `docker pull dhi.io/kafka:4.2-native` или `docker login dhi.io` |
| Kafka «не healthy» | У `dhi.io/kafka:4.2-native` нет CLI; смотрите логи: `Broker ... STARTED`. Worker ждёт TCP через `wait_for_kafka` |
| Docker build долгий | Нормально при первом запуске; повторный быстрее за счёт кэша |

---

## Порядок демонстрации (5–10 минут)

1. `docker compose up --build -d` → `docker compose ps`
2. `curl` `/health` и `/predict`
3. Grafana → дашборд (после Locust 30–60 с)
4. Prometheus → запрос `anxiety_predictions_total`
5. `docker compose logs kafka-worker | tail` — обработка Kafka
6. Показать `artifacts/` и отчёт `report/report.md`
