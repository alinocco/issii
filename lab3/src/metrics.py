"""Метрики Prometheus для сервиса инференса."""

from prometheus_client import Counter, Histogram, start_http_server

PREDICTIONS_TOTAL = Counter(
    "anxiety_predictions_total",
    "Total predictions served",
    ["source", "status"],
)

PREDICTION_LATENCY = Histogram(
    "anxiety_prediction_latency_seconds",
    "Prediction latency in seconds",
    ["source"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)


def start_metrics_server(port: int) -> None:
    start_http_server(port)
    print(f"Prometheus metrics: http://0.0.0.0:{port}/metrics")
