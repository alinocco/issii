"""
Предобработка датасета опроса по тревожности и ментальному здоровью.

Шаги:
1. Считывает основной CSV-файл из MinIO `raw/`.
2. Очищает данные и строит агрегированные шкалы (anxiety/stress/sleep/...).
3. Формирует бинарную целевую переменную тревожности, если это возможно.
4. Сохраняет результат в:
   - staging/anxiety_features.parquet
   - processed/final_anxiety_dataset.parquet

Скрипт специально написан максимально универсально: если реальные имена колонок
в датасете отличаются, достаточно подправить константы ниже
или переопределить их через переменные окружения.
"""

import os
import sys
from typing import List, Optional, Tuple

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from minio_utils import download_csv, upload_df, list_keys  # noqa: E402


RESPONDENT_ID_ENV = "RESPONDENT_ID_COL"
TARGET_COLUMN_ENV = "TARGET_COLUMN"

DEFAULT_RESPONDENT_ID = "respondent_id"
DEFAULT_TARGET_COLUMN = "anxiety_binary"

STAGING_KEY = "staging/anxiety_features.parquet"
FINAL_KEY = "processed/final_anxiety_dataset.parquet"


def _detect_id_column(df: pd.DataFrame) -> str:
    """Пытается найти колонку с идентификатором респондента."""
    candidates = [
        os.getenv(RESPONDENT_ID_ENV),
        DEFAULT_RESPONDENT_ID,
        "Respondent_ID",
        "respondentID",
        "id",
        "ID",
        "participant_id",
        "user_id",
    ]
    for col in candidates:
        if col and col in df.columns:
            return col

    # Если явного идентификатора нет — создаём его из индекса
    new_col = os.getenv(RESPONDENT_ID_ENV, DEFAULT_RESPONDENT_ID)
    df[new_col] = df.index.astype(str)
    print(f"[WARN] Явного ID-столбца не найдено, создан {new_col} по индексу.")
    return new_col


def _build_scales(df: pd.DataFrame, numeric_cols: List[str]) -> Tuple[pd.DataFrame, List[str]]:
    """Строит композитные шкалы по ключевым словам в названиях колонок."""
    df = df.copy()
    added_cols: List[str] = []

    def add_scale(keyword: str, new_name: str) -> None:
        cols = [c for c in numeric_cols if keyword in c.lower()]
        if not cols:
            return
        df[new_name] = df[cols].mean(axis=1)
        added_cols.append(new_name)
        print(f"[INFO] Шкала '{new_name}' по колонкам: {cols}")

    add_scale("anxiety", "anxiety_score")
    add_scale("stress", "stress_score")
    add_scale("sleep", "sleep_quality_score")
    add_scale("insomnia", "insomnia_score")
    add_scale("support", "support_score")
    add_scale("depress", "depression_score")

    return df, added_cols


def _ensure_target(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    """
    Обеспечивает наличие бинарной целевой переменной тревожности.

    Логика:
    1. Если в данных уже есть колонка TARGET_COLUMN_ENV/DEFAULT_TARGET_COLUMN — используем её.
    2. Иначе, если есть anxiety_score — строим anxiety_binary по медиане.
    """
    df = df.copy()
    configured_target = os.getenv(TARGET_COLUMN_ENV, DEFAULT_TARGET_COLUMN)

    if configured_target in df.columns:
        print(f"[INFO] Используем существующую целевую колонку: {configured_target}")
        return df, configured_target

    # Если есть anxiety_score — строим бинарную цель
    if "anxiety_score" in df.columns:
        median = df["anxiety_score"].median()
        df[DEFAULT_TARGET_COLUMN] = (df["anxiety_score"] >= median).astype(int)
        print(
            f"[INFO] Построена бинарная цель '{DEFAULT_TARGET_COLUMN}' "
            f"по медиане anxiety_score={median:.3f}"
        )
        return df, DEFAULT_TARGET_COLUMN

    raise ValueError(
        "Не удалось определить целевую переменную тревожности.\n"
        f"Добавьте колонку '{configured_target}' в датасет или убедитесь, что "
        "есть числовые колонки с подстрокой 'anxiety' для построения anxiety_score."
    )


def _load_raw_from_minio() -> pd.DataFrame:
    """Находит первый CSV в raw/ и загружает его."""
    keys = [k for k in list_keys("raw/") if k.endswith(".csv")]
    if not keys:
        raise FileNotFoundError(
            "В бакете нет CSV-файлов в префиксе raw/.\n"
            "Скачайте датасет с Kaggle и поместите CSV в lab1/data/raw,\n"
            "затем выполните: python scripts/download_raw_data.py"
        )

    key = sorted(keys)[0]
    print(f"[INFO] Используем сырые данные: s3://{os.getenv('MINIO_BUCKET', 'mental-health-lake')}/{key}")
    df = download_csv(key)
    print(f"[INFO] Сырые данные: shape={df.shape}")
    return df


def run() -> None:
    print("=== Anxiety survey preprocessing: start ===")
    df = _load_raw_from_minio()

    # Удаляем полностью пустые колонки
    df = df.dropna(axis=1, how="all")

    # Определяем ID-колонку
    id_col = _detect_id_column(df)
    df[id_col] = df[id_col].astype(str)

    # Выделяем числовые и категориальные колонки
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = [c for c in df.columns if c not in numeric_cols]

    print(f"[INFO] numeric_cols={len(numeric_cols)}, categorical_cols={len(categorical_cols)}")

    # Строим композитные шкалы
    df, scale_cols = _build_scales(df, numeric_cols)

    # Обновляем списки колонок после добавления шкал
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    # Базовая обработка пропусков
    if numeric_cols:
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
    if categorical_cols:
        df[categorical_cols] = df[categorical_cols].fillna("unknown")

    # Обеспечиваем наличие целевой переменной
    df, target_col = _ensure_target(df)

    # Убираем явные дубликаты по ID
    before = len(df)
    df = df.drop_duplicates(subset=[id_col])
    after = len(df)
    if after < before:
        print(f"[INFO] Удалено дубликатов по {id_col}: {before - after}")

    # Финальный набор признаков
    feature_cols: List[str] = sorted(
        {c for c in df.columns if c not in {target_col} and not c.startswith("Unnamed:")}
    )
    final_df = df[[id_col, target_col] + [c for c in feature_cols if c != id_col]]

    print(f"[INFO] Финальный датасет: shape={final_df.shape}, target={target_col}")
    class_balance = final_df[target_col].value_counts(normalize=True)
    print(f"[INFO] Баланс классов:\n{class_balance}")

    # Сохраняем в staging и processed
    upload_df(final_df, STAGING_KEY)
    upload_df(final_df, FINAL_KEY)
    print("=== Anxiety survey preprocessing: done ===")


if __name__ == "__main__":
    run()

