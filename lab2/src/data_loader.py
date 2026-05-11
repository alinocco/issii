"""
Загрузка итогового датасета с признаками тревожности.

Варианты источника данных:
  - локальный parquet-файл (LOCAL_DATA_PATH),
  - MinIO (ключ FEATURES_KEY в бакете MINIO_BUCKET).
"""

from pathlib import Path
import io

import boto3
import pandas as pd
from botocore.client import Config

from .config import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_BUCKET,
    LOCAL_DATA_PATH,
    FEATURES_KEY,
    TARGET_COLUMN,
    RESPONDENT_ID_COL,
    RANDOM_STATE,
    TEST_SIZE,
    VALIDATION_SIZE,
)


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _load_from_local() -> pd.DataFrame | None:
    if not LOCAL_DATA_PATH:
        return None
    path = Path(LOCAL_DATA_PATH)
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    print(f"Загружен локальный датасет: {path} shape={df.shape}")
    return df


def _load_from_minio() -> pd.DataFrame:
    client = _get_s3_client()
    resp = client.get_object(Bucket=MINIO_BUCKET, Key=FEATURES_KEY)
    df = pd.read_parquet(io.BytesIO(resp["Body"].read()))
    print(f"Загружен датасет из MinIO: s3://{MINIO_BUCKET}/{FEATURES_KEY} shape={df.shape}")
    return df


def load_dataset() -> pd.DataFrame:
    """
    Загружает итоговый датасет с признаками и целевой переменной тревожности.
    """
    df = _load_from_local()
    if df is None:
        df = _load_from_minio()

    if TARGET_COLUMN not in df.columns:
        raise KeyError(f"В датасете нет целевой колонки '{TARGET_COLUMN}'")

    print(f"Баланс классов по {TARGET_COLUMN}:")
    print(df[TARGET_COLUMN].value_counts(normalize=True))
    return df


def prepare_train_test_val(df: pd.DataFrame):
    """
    Разделяет датасет на обучающую, валидационную и тестовую выборки.

    Возвращает:
        X_train, X_val, X_test, y_train, y_val, y_test, feature_cols
    """
    from sklearn.model_selection import train_test_split
    from sklearn.feature_selection import VarianceThreshold

    target = TARGET_COLUMN
    id_col = RESPONDENT_ID_COL if RESPONDENT_ID_COL in df.columns else None

    exclude = {target}
    if id_col:
        exclude.add(id_col)

    # Используем только числовые признаки, категориальные будут обрабатываться отдельно при необходимости
    numeric_cols = df.select_dtypes(include=["number"]).columns
    feature_cols = [c for c in numeric_cols if c not in exclude]

    X = df[feature_cols].copy()
    y = df[target].copy()

    # Заполняем пропуски медианой
    X = X.fillna(X.median())

    # Удаление константных признаков
    selector = VarianceThreshold(threshold=0.0)
    X = pd.DataFrame(selector.fit_transform(X), columns=X.columns[selector.get_support()])
    feature_cols = list(X.columns)

    # 1. Отделяем тестовую выборку (20% от всех данных)
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    # 2. Из оставшихся 80% выделяем валидацию (25% от train_val, т.е. 20% от полного)
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val,
        y_train_val,
        test_size=VALIDATION_SIZE,
        random_state=RANDOM_STATE,
        stratify=y_train_val,
    )

    print(f"Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")

    return X_train, X_val, X_test, y_train, y_val, y_test, feature_cols

