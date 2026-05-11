# Лабораторная работа 2: Обучение модели (тревожность)

## Цель

Построить и сравнить несколько моделей классификации уровня тревожности
по итоговому датасету, подготовленному в lab1 (`final_anxiety_dataset.parquet`),
и логировать все эксперименты в MLflow.

## Зависимости и установка

Рекомендуемый способ — через Poetry:

```bash
cd lab2/
poetry install
```

## Откуда берутся данные

Модуль `src.data_loader` поддерживает два варианта источника данных:

- **Локальный parquet**:
  - Установить переменную окружения `LOCAL_DATA_PATH`, указывающую на файл
    `final_anxiety_dataset.parquet`, например:
    ```bash
    export LOCAL_DATA_PATH="/path/to/final_anxiety_dataset.parquet"
    ```
- **MinIO**:
  - Если `LOCAL_DATA_PATH` не задан, данные читаются из MinIO:
    - бакет: `MINIO_BUCKET` (по умолчанию `mental-health-lake`);
    - ключ: `FEATURES_KEY` (по умолчанию `processed/final_anxiety_dataset.parquet`).

Целевая колонка: `TARGET_COLUMN` (по умолчанию `anxiety_binary`).  
Идентификатор респондента: `RESPONDENT_ID_COL` (по умолчанию `respondent_id`).

## Настройка MLflow

В `src/config.py` по умолчанию:

- `MLFLOW_TRACKING_URI = "http://localhost:5000"`
- `MLFLOW_EXPERIMENT_NAME = "anxiety_classification"`

Можно переопределить их через переменные окружения:

```bash
export MLFLOW_TRACKING_URI="http://localhost:5000"
export MLFLOW_EXPERIMENT_NAME="anxiety_lab2"
```

После запуска трекинг-сервера MLflow UI будет доступен по адресу
`http://localhost:5000` (если используется стандартный сервер).

## Запуск одного эксперимента

Пример: запуск только базовой логистической регрессии:

```bash
cd lab2/
poetry run python -m src.experiment --model logistic
```

Модель обучится, посчитает метрики (F1, ROC-AUC и др.), построит графики
и залогирует всё в MLflow.

## Запуск полного набора экспериментов

```bash
cd lab2/
poetry run python -m src.experiment
```

Будут последовательно запущены:

- **Baseline**: логистическая регрессия с разными `C`;
- **Гипотеза 1**: ансамблевые модели (RandomForest, XGBoost, LightGBM);
- **Гипотеза 2**: отбор признаков (SelectKBest + LogisticRegression);
- **Гипотеза 3**: работа с дисбалансом (class_weight и SMOTE для RandomForest).

По итогам в консоль выведется сводная таблица по метрикам (F1, ROC-AUC и др.)
и будет напечатана лучшая конфигурация.

## Формат экспериментов в MLflow

Для каждого запуска в MLflow логируются:

- параметры модели и предобработки;
- качество на валидации и тесте (`val_f1`, `test_f1`, `val_roc_auc`, `test_roc_auc` и др.);
- артефакты:
  - матрица ошибок (`confusion_matrix.png`);
  - ROC-кривая (`roc_curve.png`);
  - важность признаков (`feature_importance.png`);
  - кривая валидации по одному из гиперпараметров (`validation_curve.png`), если определена;
- сама обученная модель (через `mlflow.sklearn.log_model`).

