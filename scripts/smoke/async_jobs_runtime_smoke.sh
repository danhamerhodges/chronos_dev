#!/usr/bin/env bash
set -euo pipefail

if [[ "${CHRONOS_RUN_ASYNC_RUNTIME_SMOKE:-0}" != "1" ]]; then
  echo "Set CHRONOS_RUN_ASYNC_RUNTIME_SMOKE=1 to run the async jobs runtime smoke."
  exit 1
fi

./.venv/bin/python scripts/smoke/async_jobs_runtime_smoke.py
