"""Конфигурация lab3 (деплой и инференс)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

LAB3_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", LAB3_ROOT / "artifacts"))

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "mental-health-lake")

LOCAL_DATA_PATH = os.getenv("LOCAL_DATA_PATH")
FEATURES_KEY = os.getenv("FEATURES_KEY", "processed/final_anxiety_dataset.parquet")
TARGET_COLUMN = os.getenv("TARGET_COLUMN", "anxiety_binary")
RESPONDENT_ID_COL = os.getenv("RESPONDENT_ID_COL", "respondent_id")

RANDOM_STATE = 42
TEST_SIZE = 0.2
VALIDATION_SIZE = 0.25

MODEL_NAME = os.getenv("MODEL_NAME", "logistic")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_INPUT_TOPIC = os.getenv("KAFKA_INPUT_TOPIC", "anxiety.features")
KAFKA_OUTPUT_TOPIC = os.getenv("KAFKA_OUTPUT_TOPIC", "anxiety.predictions")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "anxiety-inference-worker")

BENTO_HOST = os.getenv("BENTO_HOST", "localhost")
BENTO_PORT = int(os.getenv("BENTO_PORT", "3000"))

PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_METRICS_PORT", "9091"))
