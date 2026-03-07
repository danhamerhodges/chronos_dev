#!/usr/bin/env bash
set -euo pipefail

if [[ "${CHRONOS_RUN_REALTIME_DIAGNOSTIC:-0}" != "1" ]]; then
  echo "Set CHRONOS_RUN_REALTIME_DIAGNOSTIC=1 to run the realtime progress diagnostic."
  exit 1
fi

./.venv/bin/python scripts/smoke/realtime_progress_diagnostic.py
