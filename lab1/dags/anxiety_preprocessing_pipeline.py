"""
DAG: anxiety_preprocessing_pipeline

Граф задач:
  check_raw_data
        |
  survey_preprocess
        |
  validate_staging
        |
  check_increment
        |
  load_increment  (если есть новые файлы в increment/)
        |
  pipeline_complete
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator

sys.path.insert(0, "/opt/airflow/scripts")

DEFAULT_ARGS = {
    "owner": "lab1-anxiety",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


def _check_raw_data(**ctx) -> str:
    """Проверяет, загружены ли уже сырые данные опроса в MinIO."""
    import minio_utils

    keys = minio_utils.list_keys("raw/")
    csv_keys = [k for k in keys if k.endswith(".csv")]
    if csv_keys:
        print(f"Raw data OK: найдено {len(csv_keys)} CSV-файлов.")
        return "survey_preprocess"

    print("Raw data не найдены. Нужна ручная загрузка.")
    raise FileNotFoundError(
        "Загрузите CSV-файлы датасета опроса по тревожности в lab1/data/raw/ "
        "и выполните: python scripts/download_raw_data.py"
    )


def _validate_staging(**ctx) -> None:
    """Проверяет, что staging/anxiety_features.parquet существует и выглядит разумно."""
    import pandas as pd
    import minio_utils

    key = "staging/anxiety_features.parquet"
    df = minio_utils.download_df(key)
    assert len(df) > 0, f"{key} пустой!"

    respondent_id_col = os.getenv("RESPONDENT_ID_COL", "respondent_id")
    target_col = os.getenv("TARGET_COLUMN", "anxiety_binary")

    if respondent_id_col not in df.columns:
        raise AssertionError(f"{key}: нет ID-колонки {respondent_id_col}")
    if target_col not in df.columns:
        raise AssertionError(f"{key}: нет целевой колонки {target_col}")

    print(f"[OK] {key}: {df.shape}")
    print(f"[OK] Целевая колонка: {target_col}, баланс классов:\n{df[target_col].value_counts(normalize=True)}")

    null_ratio = df.isnull().mean()
    high_null = null_ratio[null_ratio > 0.5]
    if len(high_null) > 0:
        print(f"[WARN] Колонки с >50% пропусков: {high_null.index.tolist()}")


def _check_increment(**ctx) -> str:
    """Ветвление: есть ли инкремент?"""
    import minio_utils

    keys = minio_utils.list_keys("increment/")
    new_files = [
        k for k in keys if (k.endswith(".csv") or k.endswith(".parquet")) and "done/" not in k
    ]
    if new_files:
        print(f"Найден инкремент: {new_files}")
        return "load_increment"

    print("Инкремента нет.")
    return "pipeline_complete"


def _pipeline_complete(**ctx) -> None:
    print("Anxiety preprocessing pipeline завершён успешно.")


with DAG(
    dag_id="anxiety_preprocessing_pipeline",
    default_args=DEFAULT_ARGS,
    description="Предобработка данных опроса по тревожности",
    schedule_interval="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["lab1", "preprocessing", "anxiety"],
) as dag:

    check_raw = PythonOperator(
        task_id="check_raw_data",
        python_callable=_check_raw_data,
    )

    def _run_survey_preprocess(**ctx):
        import preprocess_survey

        preprocess_survey.run()

    def _run_increment(**ctx):
        import load_increment

        return load_increment.run()

    survey_preprocess = PythonOperator(
        task_id="survey_preprocess",
        python_callable=_run_survey_preprocess,
    )

    validate_staging = PythonOperator(
        task_id="validate_staging",
        python_callable=_validate_staging,
    )

    check_incr = BranchPythonOperator(
        task_id="check_increment",
        python_callable=_check_increment,
    )

    task_increment = PythonOperator(
        task_id="load_increment",
        python_callable=_run_increment,
    )

    task_done = PythonOperator(
        task_id="pipeline_complete",
        python_callable=_pipeline_complete,
        trigger_rule="none_failed_min_one_success",
    )

    check_raw >> survey_preprocess >> validate_staging >> check_incr
    check_incr >> [task_increment, task_done]
    task_increment >> task_done

