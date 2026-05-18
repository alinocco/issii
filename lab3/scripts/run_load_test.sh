#!/usr/bin/env bash
# Headless Locust: 50 users, 10/s spawn, 60s
set -euo pipefail
cd "$(dirname "$0")/.."
HOST="${BENTO_HOST:-http://localhost:3000}"
locust -f load_test/locustfile.py \
  --host "$HOST" \
  --headless \
  -u 50 \
  -r 10 \
  -t 60s \
  --html reports/locust_report.html \
  --csv reports/locust

echo "Отчёты: reports/locust_report.html, reports/locust_stats.csv"
