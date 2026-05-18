"""
Конфигурация лабораторной работы 2 (тревожность).

Настройки по умолчанию читаются из переменных окружения.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")
MLFLOW_EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "anxiety_classification")

# MinIO
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "mental-health-lake")

# Данные
LOCAL_DATA_PATH = os.getenv("LOCAL_DATA_PATH")  # если указан, берём parquet локально
FEATURES_KEY = os.getenv("FEATURES_KEY", "processed/final_anxiety_dataset.parquet")
TARGET_COLUMN = os.getenv("TARGET_COLUMN", "anxiety_binary")
RESPONDENT_ID_COL = os.getenv("RESPONDENT_ID_COL", "respondent_id")

# Обучение
RANDOM_STATE = 42
TEST_SIZE = 0.2
VALIDATION_SIZE = 0.25  # доля от train_val (80% данных) -> 0.25*0.8 = 0.2 от полного

