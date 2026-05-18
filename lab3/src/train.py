"""Обучение модели (пайплайны из lab2)."""

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


def build_model(model_name: str, **params):
    params.setdefault("random_state", 42)

    if model_name == "logistic":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=2000,
                        C=params.get("C", 1.0),
                        class_weight="balanced",
                        solver="lbfgs",
                        random_state=params["random_state"],
                    ),
                ),
            ]
        )
    if model_name == "random_forest":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=params.get("n_estimators", 200),
                        max_depth=params.get("max_depth", 15),
                        random_state=params["random_state"],
                        n_jobs=-1,
                    ),
                ),
            ]
        )
    if model_name == "xgboost":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    XGBClassifier(
                        n_estimators=params.get("n_estimators", 300),
                        max_depth=params.get("max_depth", 6),
                        learning_rate=params.get("learning_rate", 0.1),
                        random_state=params["random_state"],
                        eval_metric="logloss",
                    ),
                ),
            ]
        )
    raise ValueError(f"Unknown model: {model_name}")
