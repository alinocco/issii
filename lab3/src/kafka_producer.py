"""
Публикация запросов на инференс в Kafka (источник данных для пайплайна).

Запуск:
    python -m src.kafka_producer --limit 1000
"""

import argparse
import json
import time
import uuid

from confluent_kafka import Producer

from .config import (
    ARTIFACTS_DIR,
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_INPUT_TOPIC,
    MODEL_NAME,
)
from .data_loader import load_dataset, prepare_splits
from .wait_for_kafka import wait_for_kafka


def main():
    wait_for_kafka()
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500, help="Число сообщений")
    parser.add_argument("--delay-ms", type=int, default=0, help="Пауза между сообщениями")
    args = parser.parse_args()

    df = load_dataset()
    _, _, X_test, _, _, _, feature_names = prepare_splits(df)

    producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS})

    n = min(args.limit, len(X_test))
    print(f"Публикация {n} сообщений в topic={KAFKA_INPUT_TOPIC}")

    for i in range(n):
        row = X_test.iloc[i]
        message = {
            "request_id": str(uuid.uuid4()),
            "features": {name: float(row[name]) for name in feature_names},
        }
        producer.produce(
            KAFKA_INPUT_TOPIC,
            key=message["request_id"].encode(),
            value=json.dumps(message).encode("utf-8"),
        )
        producer.poll(0)
        if args.delay_ms:
            time.sleep(args.delay_ms / 1000.0)

    producer.flush()
    print(f"Готово. artifacts={ARTIFACTS_DIR / MODEL_NAME}")


if __name__ == "__main__":
    main()
