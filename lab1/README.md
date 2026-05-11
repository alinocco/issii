# Лабораторная работа 1: Предобработка данных (тревожность)

## Постановка задачи

Предсказание уровня тревожности (бинарная классификация) по данным опроса о ментальном здоровье:
демография, стресс, сон, социальная поддержка и сопутствующие факторы.

Целевая переменная по умолчанию: `anxiety_binary`  
(1 — повышенная тревожность, 0 — нет; строится по агрегированной шкале тревожности или берётся
из готового столбца, см. `scripts/preprocess_survey.py`).

Метрики оценки модели (для последующей lab2): **F1-score** (основная при возможном дисбалансе),
а также **ROC-AUC, Precision, Recall**.

## Выбор хранилища — MinIO (локальный S3)

Обоснование:
- S3-совместимый API — промышленный стандарт для data lake.
- Легко разворачивается в Docker без облачных расходов.
- Слоистая структура хранения: `raw/` → `staging/` → `processed/` + `increment/` для дозагрузки.
- При необходимости можно прозрачно заменить на облачный S3/Yandex Object Storage.

Бакет по умолчанию: `mental-health-lake`.

## Запуск инфраструктуры

```bash
cd lab1/
docker compose up -d
```

Сервисы:
- Airflow (web + scheduler + Postgres для метаданных).
- MinIO (S3-хранилище + web-консоль).

## Подготовка данных

1. **Скачать датасет с Kaggle**

Например, датасет про тревожность `Mental Health Data (Anxiety)` (или любой аналогичный
опрос по ментальному здоровью).

```bash
cd lab1/data/raw
# пример для Kaggle CLI (нужно настроить токен ~/.kaggle/kaggle.json)
kaggle datasets download -d michellevp/predicting-anxiety-in-mental-health-data --unzip
```

Важно: в итоге в `lab1/data/raw` должны лежать один или несколько CSV-файлов с ответами опроса.

2. **Загрузка сырых CSV в MinIO**

```bash
cd lab1/
python scripts/download_raw_data.py
```

Скрипт найдёт все `*.csv` в `data/raw/` и загрузит их в бакет `mental-health-lake` в префикс `raw/`.

## Запуск пайплайна

1. Открыть Airflow UI: `http://localhost:8081`  
   Логин: `admin` / Пароль: `admin`

2. Убедиться, что DAG `anxiety_preprocessing_pipeline` в состоянии *unpaused*.

3. Нажать **Trigger DAG** для `anxiety_preprocessing_pipeline`.

## Просмотр данных в MinIO

Открыть MinIO UI: `http://localhost:9001`  
Логин: `minioadmin` / Пароль: `minioadmin`

В бакете `mental-health-lake` будут использоваться префиксы:
- `raw/` — сырые CSV с ответами опроса.
- `staging/` — промежуточные parquet с признаками (`anxiety_features.parquet`).
- `processed/` — финальный датасет для обучения (`final_anxiety_dataset.parquet`).
- `increment/` — файлы для инкрементальной дозагрузки.

## Структура проекта

```text
lab1/
├── docker-compose.yml          # Airflow + MinIO + PostgreSQL
├── Dockerfile                  # Airflow + зависимости
├── requirements.txt
├── dags/
│   └── anxiety_preprocessing_pipeline.py   # Основной DAG
├── scripts/
│   ├── minio_utils.py          # Утилиты для работы с MinIO
│   ├── download_raw_data.py    # Загрузка локальных CSV в MinIO (raw/)
│   ├── preprocess_survey.py    # Предобработка и построение признаков опроса
│   ├── load_increment.py       # Инкрементальная дозагрузка
│   └── build_increment_sample.py  # Генерация демо-инкремента из processed
├── notebooks/
│   └── eda_anxiety.ipynb       # EDA по датасету опроса (опционально)
└── data/
    ├── raw/                    # Исходные CSV с Kaggle
    └── increment/              # Файлы для инкрементальной загрузки
```

## DAG: anxiety_preprocessing_pipeline

| Задача              | Описание |
|---------------------|----------|
| `check_raw_data`    | Проверяет наличие CSV в MinIO `raw/`, иначе просит запустить `scripts/download_raw_data.py`. |
| `survey_preprocess` | Запускает `preprocess_survey.py`: читает сырые ответы, строит шкалы тревожности/стресса/сна и формирует финальный датасет. |
| `validate_staging`  | Проверяет, что `staging/anxiety_features.parquet` не пустой и содержит ID и целевую колонку. |
| `check_increment`   | Ветвление: есть ли новые файлы в `increment/`? |
| `load_increment`    | Если инкремент есть — дозагружает новые записи в `processed/final_anxiety_dataset.parquet` с дедупликацией. |
| `pipeline_complete` | Завершение пайплайна. |

Расписание: `@daily` (демонстрация регулярного запуска).

## Инкрементальная загрузка

### Быстрый демо-инкремент (из части processed-датасета)

После успешного полного прогона пайплайна в MinIO появляется
`processed/final_anxiety_dataset.parquet`. Скрипт берёт случайные строки,
присваивает им новые идентификаторы респондента и кладёт parquet в `data/increment/`
и в MinIO `increment/`:

```bash
python scripts/build_increment_sample.py -n 400
```

Флаг `--no-upload` — только локальный файл (без загрузки в MinIO).

При следующем запуске DAG шаг `load_increment` обработает файл и дополнит
`processed/final_anxiety_dataset.parquet` новыми записями.

