#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from app.observability.monitoring import metrics_payload

payload = metrics_payload("chronos")
print(payload)
if "# TYPE" not in payload:
    raise SystemExit(1)
PY
