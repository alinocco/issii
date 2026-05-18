"""Синтетический датасет для локальной отладки без MinIO."""

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "sample_anxiety.parquet"


def main():
    rng = np.random.default_rng(42)
    n = 2000
    anxiety_score = rng.uniform(0, 1, n)
    stress_score = rng.uniform(0, 1, n)
    sleep_quality_score = rng.uniform(0, 1, n)
    support_score = rng.uniform(0, 1, n)
    insomnia_score = rng.uniform(0, 1, n)

    anxiety_binary = (
        (anxiety_score > 0.55)
        | (stress_score > 0.6)
        | (sleep_quality_score < 0.35)
    ).astype(int)

    df = pd.DataFrame(
        {
            "respondent_id": [f"r{i}" for i in range(n)],
            "anxiety_score": anxiety_score,
            "stress_score": stress_score,
            "sleep_quality_score": sleep_quality_score,
            "support_score": support_score,
            "insomnia_score": insomnia_score,
            "anxiety_binary": anxiety_binary,
        }
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    print(f"Saved {OUT} shape={df.shape}")


if __name__ == "__main__":
    main()
