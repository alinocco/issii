"""
Consumer Kafka: читает признаки, инференс ONNX, пишет предсказания в output topic.

Запуск:
    python -m src.kafka_consumer
"""

import json
import signal
import sys
import time

from confluent_kafka import Consumer, Producer

from .config import (
    ARTIFACTS_DIR,
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_GROUP_ID,
    KAFKA_INPUT_TOPIC,
    KAFKA_OUTPUT_TOPIC,
    MODEL_NAME,
)
from .metrics import PREDICTION_LATENCY, PREDICTIONS_TOTAL, start_metrics_server
from .onnx_runtime import OnnxAnxietyClassifier
from .config import PROMETHEUS_PORT
from .wait_for_kafka import wait_for_kafka


_running = True


def _shutdown(*_):
    global _running
    _running = False


def main():
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    wait_for_kafka()
    start_metrics_server(PROMETHEUS_PORT)
    classifier = OnnxAnxietyClassifier(ARTIFACTS_DIR / MODEL_NAME)

    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": KAFKA_GROUP_ID,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )
    producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS})
    consumer.subscribe([KAFKA_INPUT_TOPIC])

    print(f"Worker слушает {KAFKA_INPUT_TOPIC} -> {KAFKA_OUTPUT_TOPIC}")

    while _running:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"Kafka error: {msg.error()}", file=sys.stderr)
            continue

        start = time.perf_counter()
        try:
            payload = json.loads(msg.value().decode("utf-8"))
            request_id = payload.get("request_id", "unknown")
            features = payload["features"]
            result = classifier.predict(features)
            out = {
                "request_id": request_id,
                **result,
            }
            producer.produce(
                KAFKA_OUTPUT_TOPIC,
                key=request_id.encode(),
                value=json.dumps(out).encode("utf-8"),
            )
            producer.poll(0)
            PREDICTIONS_TOTAL.labels(source="kafka", status="ok").inc()
        except Exception as exc:
            PREDICTIONS_TOTAL.labels(source="kafka", status="error").inc()
            print(f"Ошибка обработки: {exc}", file=sys.stderr)
        finally:
            PREDICTION_LATENCY.labels(source="kafka").observe(time.perf_counter() - start)

    consumer.close()
    producer.flush()
    print("Worker остановлен.")


if __name__ == "__main__":
    main()
