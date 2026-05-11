"""
Инкрементальная загрузка для датасета по тревожности.

Логика:
1. Ищет новые файлы в префиксе increment/ (CSV или Parquet).
2. Считывает их, объединяет между собой.
3. Подмешивает к processed/final_anxiety_dataset.parquet с дедупликацией по ID.
4. Обновлённый датасет сохраняет в тот же ключ processed/final_anxiety_dataset.parquet.
5. Обработанные файлы переносит в increment/done/.
"""

import io
import os
import sys
from typing import List, Dict, Any

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from minio_utils import (  # noqa: E402
    download_df,
    upload_df,
    get_s3_client,
    list_keys,
    key_exists,
)


BUCKET = os.getenv("MINIO_BUCKET", "mental-health-lake")
FINAL_KEY = "processed/final_anxiety_dataset.parquet"
RESPONDENT_ID_ENV = "RESPONDENT_ID_COL"
DEFAULT_RESPONDENT_ID = "respondent_id"


def _move_processed_increment(s3_key: str) -> None:
    """Перемещает обработанный файл из increment/ в increment/done/."""
    client = get_s3_client()
    new_key = s3_key.replace("increment/", "increment/done/", 1)
    client.copy_object(Bucket=BUCKET, CopySource={"Bucket": BUCKET, "Key": s3_key}, Key=new_key)
    client.delete_object(Bucket=BUCKET, Key=s3_key)
    print(f"[INFO] Moved {s3_key} -> {new_key}")


def _load_existing() -> pd.DataFrame:
    if not key_exists(FINAL_KEY):
        print("[INFO] Финального датасета ещё нет, начинаем с пустого.")
        return pd.DataFrame()
    return download_df(FINAL_KEY)


def _detect_id_column(df: pd.DataFrame) -> str:
    candidate = os.getenv(RESPONDENT_ID_ENV, DEFAULT_RESPONDENT_ID)
    if candidate in df.columns:
        return candidate
    for alt in ["Respondent_ID", "respondentID", "id", "ID", "participant_id", "user_id"]:
        if alt in df.columns:
            return alt
    raise ValueError(
        "Не удалось найти идентификатор респондента в инкрементальных данных.\n"
        "Установите RESPONDENT_ID_COL или приведите датасет к ожидаемой схеме."
    )


def run() -> Dict[str, Any]:
    """
    Возвращает {"new_rows": int} — сколько строк добавлено.
    Если инкремента нет, возвращает {"new_rows": 0}.
    """
    print("=== Anxiety increment load: start ===")
    increment_keys: List[str] = [
        k
        for k in list_keys("increment/")
        if (k.endswith(".csv") or k.endswith(".parquet")) and "done/" not in k
    ]

    if not increment_keys:
        print("[INFO] Инкрементальных файлов нет.")
        return {"new_rows": 0}

    print(f"[INFO] Найдено файлов инкремента: {len(increment_keys)}")
    client = get_s3_client()
    parts: List[pd.DataFrame] = []

    for key in increment_keys:
        print(f"[INFO] Обрабатываем {key}")
        response = client.get_object(Bucket=BUCKET, Key=key)
        raw_bytes = response["Body"].read()

        if key.endswith(".csv"):
            chunk = pd.read_csv(io.BytesIO(raw_bytes))
        else:
            chunk = pd.read_parquet(io.BytesIO(raw_bytes))

        parts.append(chunk)
        _move_processed_increment(key)

    if not parts:
        print("[INFO] Нет данных после чтения инкремента.")
        return {"new_rows": 0}

    new_data = pd.concat(parts, ignore_index=True)
    print(f"[INFO] Всего строк в инкременте: {len(new_data)}")

    existing = _load_existing()
    if existing.empty:
        combined = new_data
    else:
        id_col = _detect_id_column(existing)
        if id_col in new_data.columns:
            before = len(new_data)
            new_data = new_data[~new_data[id_col].isin(existing[id_col])]
            print(f"[INFO] Отфильтровано дубликатов по {id_col}: {before - len(new_data)}")
        combined = pd.concat([existing, new_data], ignore_index=True)

    added = len(combined) - len(existing)
    if added <= 0:
        print("[INFO] Новых записей не найдено.")
        return {"new_rows": 0}

    upload_df(combined, FINAL_KEY)
    print(f"=== Anxiety increment load: done. Добавлено строк: {added} ===")
    return {"new_rows": int(added)}


if __name__ == "__main__":
    result = run()
    print(result)

