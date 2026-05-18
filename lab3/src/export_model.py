"""
Обучение модели (как в lab2) и экспорт в ONNX + joblib + метаданные признаков.

Запуск:
    python -m src.export_model
    python -m src.export_model --model random_forest
"""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

from .config import ARTIFACTS_DIR, MODEL_NAME
from .data_loader import load_dataset, prepare_splits
from .train import build_model


def export_pipeline(model, feature_names: list[str], out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    sklearn_path = out_dir / "model.joblib"
    joblib.dump(model, sklearn_path)

    n_features = len(feature_names)
    initial_type = [("input", FloatTensorType([None, n_features]))]
    onnx_model = convert_sklearn(
        model,
        initial_types=initial_type,
        target_opset=17,
        options={type(model): {"zipmap": False}},
    )
    onnx_path = out_dir / "model.onnx"
    with open(onnx_path, "wb") as f:
        f.write(onnx_model.SerializeToString())

    meta = {
        "feature_names": feature_names,
        "n_features": n_features,
        "output_names": ["label", "probabilities"],
    }
    meta_path = out_dir / "model_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"sklearn": sklearn_path, "onnx": onnx_path, "meta": meta_path}


def main():
    parser = argparse.ArgumentParser(description="Train and export anxiety classifier")
    parser.add_argument("--model", default=MODEL_NAME, choices=["logistic", "random_forest", "xgboost"])
    parser.add_argument("--out-dir", type=Path, default=ARTIFACTS_DIR)
    args = parser.parse_args()

    print("Загрузка данных...")
    df = load_dataset()
    X_train, X_val, X_test, y_train, y_val, y_test, feature_names = prepare_splits(df)

    print(f"Обучение модели: {args.model}")
    model = build_model(args.model)
    model.fit(X_train, y_train)

    val_score = model.score(X_val, y_val)
    test_score = model.score(X_test, y_test)
    print(f"Accuracy val={val_score:.4f} test={test_score:.4f}")

    out_dir = args.out_dir / args.model
    paths = export_pipeline(model, feature_names, out_dir)
    print("Экспорт завершён:")
    for name, path in paths.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
