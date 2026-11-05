#!/usr/bin/env bash
# usage: scripts/loadtest.sh [run-time] [csv-prefix]   (standard command from the handout)
set -euo pipefail
RT=${1:-2m}; PREFIX=${2:-results/loadtest}
mkdir -p results
LOADTEST_HEADERS_OUT=${PREFIX}_headers.json locust -f tools/locustfile.py --headless --users 4 --spawn-rate 4 \
  --run-time "$RT" --host http://localhost:8080 --csv "$PREFIX" || true
