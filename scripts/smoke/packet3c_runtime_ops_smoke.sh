#!/usr/bin/env bash
set -euo pipefail

if [[ "${CHRONOS_RUN_PACKET3C_RUNTIME_SMOKE:-0}" != "1" ]]; then
  echo "Set CHRONOS_RUN_PACKET3C_RUNTIME_SMOKE=1 to run the Packet 3C runtime ops smoke."
  exit 1
fi

./.venv/bin/python scripts/smoke/packet3c_runtime_ops_smoke.py
