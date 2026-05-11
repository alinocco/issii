"""
Строит файл инкремента из случайной части уже обработанного датасета
processed/final_anxiety_dataset.parquet.

Результат:
  - lab1/data/increment/anxiety_increment.parquet (локально)
  - s3://<bucket>/increment/anxiety_increment.parquet (MinIO), если не указан --no-upload.
"""

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from minio_utils import download_df, upload_df  # noqa: E402

DEFAULT_N = 400


def build_increment(n_rows: int, seed: int, upload: bool) -> str:
    processed = download_df("processed/final_anxiety_dataset.parquet")
    if processed.empty:
        raise RuntimeError("processed/final_anxiety_dataset.parquet пустой или отсутствует.")

    n = min(n_rows, len(processed))
    if n < 1:
        raise RuntimeError("processed/final_anxiety_dataset.parquet пустой.")

    sample = processed.sample(n=n, random_state=seed).reset_index(drop=True).copy()

    # Обновляем идентификатор, чтобы имитировать новых респондентов
    id_col = os.getenv("RESPONDENT_ID_COL", "respondent_id")
    if id_col not in sample.columns:
        id_col = "respondent_id"
        sample[id_col] = sample.index.astype(str)
    prefix = pd.Timestamp.utcnow().strftime("inc-%Y%m%d-")
    sample[id_col] = [f"{prefix}{i:06d}" for i in range(len(sample))]

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "increment")
    os.makedirs(out_dir, exist_ok=True)
    local_path = os.path.join(out_dir, "anxiety_increment.parquet")
    sample.to_parquet(local_path, index=False, engine="pyarrow")
    print(f"Локально: {local_path} ({len(sample)} строк, {len(sample.columns)} колонок)")

    if upload:
        upload_df(sample, "increment/anxiety_increment.parquet")
        print("MinIO: increment/anxiety_increment.parquet")

    return local_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Собрать инкремент из части processed-датасета")
    parser.add_argument("-n", type=int, default=DEFAULT_N, help="Число строк (по умолчанию 400)")
    parser.add_argument("--seed", type=int, default=42, help="random_state для sample")
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="только локальный parquet, без загрузки в MinIO",
    )
    args = parser.parse_args()
    build_increment(args.n, args.seed, upload=not args.no_upload)


if __name__ == "__main__":
    main()

