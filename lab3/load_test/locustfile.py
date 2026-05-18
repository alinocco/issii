"""
Нагрузочное тестирование REST API BentoML.

Запуск:
    locust -f load_test/locustfile.py --host http://localhost:3000
"""

import json
import random
from pathlib import Path

from locust import HttpUser, between, task

SAMPLE_FEATURES = {
    "anxiety_score": 0.72,
    "stress_score": 0.65,
    "sleep_quality_score": 0.28,
    "support_score": 0.41,
    "insomnia_score": 0.55,
}


def _load_feature_pool():
    meta_path = Path(__file__).resolve().parents[1] / "artifacts" / "logistic" / "model_meta.json"
    if meta_path.exists():
        import json as _json

        names = _json.loads(meta_path.read_text())["feature_names"]
        return names
    return list(SAMPLE_FEATURES.keys())


FEATURE_NAMES = _load_feature_pool()


class AnxietyApiUser(HttpUser):
    wait_time = between(0.01, 0.05)

    @task(10)
    def predict(self):
        features = {name: random.random() for name in FEATURE_NAMES}
        self.client.post(
            "/predict",
            json={"features": features},
            name="POST /predict",
        )

    @task(1)
    def health(self):
        self.client.post("/health", json={}, name="POST /health")
