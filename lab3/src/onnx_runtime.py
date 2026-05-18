"""Инференс через ONNX Runtime (импорт из формата ONNX)."""

import json
from pathlib import Path

import numpy as np
import onnxruntime as ort


class OnnxAnxietyClassifier:
    def __init__(self, artifacts_dir: Path):
        artifacts_dir = Path(artifacts_dir)
        meta_path = artifacts_dir / "model_meta.json"
        onnx_path = artifacts_dir / "model.onnx"

        with open(meta_path, encoding="utf-8") as f:
            self.meta = json.load(f)

        self.feature_names = self.meta["feature_names"]
        self.session = ort.InferenceSession(
            str(onnx_path),
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name

    def predict(self, features: dict[str, float] | list[float]) -> dict:
        if isinstance(features, dict):
            row = [float(features[name]) for name in self.feature_names]
        else:
            row = [float(x) for x in features]

        X = np.array([row], dtype=np.float32)
        outputs = self.session.run(None, {self.input_name: X})

        # skl2onnx: [label, probabilities] или один выход
        if len(outputs) >= 2:
            label = int(outputs[0][0])
            proba = outputs[1]
            if proba.ndim == 2 and proba.shape[1] == 2:
                score = float(proba[0, 1])
            else:
                score = float(proba[0])
        else:
            label = int(np.argmax(outputs[0]))
            score = float(outputs[0].max())

        return {
            "prediction": label,
            "probability_high_anxiety": score,
            "model_format": "onnx",
        }
