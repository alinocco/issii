"""
BentoML-сервис: импорт ONNX-модели и REST API.

Запуск (после export_model):
    bentoml serve service:AnxietyService --port 3000
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import bentoml

from src.config import ARTIFACTS_DIR, MODEL_NAME, PROMETHEUS_PORT
from src.metrics import PREDICTION_LATENCY, PREDICTIONS_TOTAL, start_metrics_server
from src.onnx_runtime import OnnxAnxietyClassifier

ARTIFACT_PATH = Path(os.getenv("ARTIFACT_PATH", ARTIFACTS_DIR / MODEL_NAME))


@bentoml.service(
    name="anxiety-classifier",
    traffic={"timeout": 30},
    resources={"cpu": "1"},
)
class AnxietyService:
    """REST-доступ к модели; инференс через ONNX Runtime."""

    def __init__(self) -> None:
        start_metrics_server(PROMETHEUS_PORT)
        self.classifier = OnnxAnxietyClassifier(ARTIFACT_PATH)

    @bentoml.api
    def predict(self, features: dict) -> dict:
        """
        POST /predict
        Body: {"features": {"anxiety_score": 0.5, ...}} или плоский dict признаков.
        """
        start = time.perf_counter()
        try:
            payload = features.get("features", features)
            result = self.classifier.predict(payload)
            PREDICTIONS_TOTAL.labels(source="rest", status="ok").inc()
            return result
        except Exception:
            PREDICTIONS_TOTAL.labels(source="rest", status="error").inc()
            raise
        finally:
            PREDICTION_LATENCY.labels(source="rest").observe(time.perf_counter() - start)

    @bentoml.api
    def health(self) -> dict:
        return {
            "status": "ok",
            "model_format": "onnx",
            "n_features": len(self.classifier.feature_names),
            "artifact_path": str(ARTIFACT_PATH),
        }

