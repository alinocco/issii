"""Ожидание готовности Kafka (для native-образа без CLI)."""

import os
import socket
import sys
import time


def wait_for_kafka(
    host: str | None = None,
    port: int = 9092,
    timeout_sec: int = 120,
    interval_sec: float = 2.0,
) -> None:
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    if host is None:
        host = bootstrap.split(",")[0].split(":")[0]
        if ":" in bootstrap.split(",")[0]:
            port = int(bootstrap.split(",")[0].split(":")[1])

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                print(f"Kafka доступна: {host}:{port}")
                return
        except OSError as exc:
            print(f"Ожидание Kafka {host}:{port}... ({exc})")
            time.sleep(interval_sec)

    print(f"Kafka не ответила за {timeout_sec}s", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    wait_for_kafka()
