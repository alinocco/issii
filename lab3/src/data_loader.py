"""Загрузка датасета (совместимо с lab2)."""

from pathlib import Path
import io

import boto3
import pandas as pd
from botocore.client import Config
from sklearn.feature_selection import VarianceThreshold
from sklearn.model_selection import train_test_split

from .config import (
    FEATURES_KEY,
    LOCAL_DATA_PATH,
    MINIO_ACCESS_KEY,
    MINIO_BUCKET,
    MINIO_ENDPOINT,
    MINIO_SECRET_KEY,
    RANDOM_STATE,
    RESPONDENT_ID_COL,
    TARGET_COLUMN,
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


def load_dataset() -> pd.DataFrame:
    if LOCAL_DATA_PATH:
        path = Path(LOCAL_DATA_PATH)
        if path.exists():
            df = pd.read_parquet(path)
            print(f"Локальный датасет: {path} shape={df.shape}")
            return df

    client = _get_s3_client()
    resp = client.get_object(Bucket=MINIO_BUCKET, Key=FEATURES_KEY)
    df = pd.read_parquet(io.BytesIO(resp["Body"].read()))
    print(f"MinIO: s3://{MINIO_BUCKET}/{FEATURES_KEY} shape={df.shape}")
    return df


def prepare_splits(df: pd.DataFrame):
    target = TARGET_COLUMN
    id_col = RESPONDENT_ID_COL if RESPONDENT_ID_COL in df.columns else None
    exclude = {target}
    if id_col:
        exclude.add(id_col)

    numeric_cols = df.select_dtypes(include=["number"]).columns
    feature_cols = [c for c in numeric_cols if c not in exclude]

    X = df[feature_cols].copy().fillna(df[feature_cols].median())
    y = df[target].copy()

    selector = VarianceThreshold(threshold=0.0)
    X = pd.DataFrame(selector.fit_transform(X), columns=X.columns[selector.get_support()])
    feature_cols = list(X.columns)

    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val,
        y_train_val,
        test_size=VALIDATION_SIZE,
        random_state=RANDOM_STATE,
        stratify=y_train_val,
    )
    return X_train, X_val, X_test, y_train, y_val, y_test, feature_cols
