#!/usr/bin/env bash
set -euo pipefail

echo "Phase 1 bootstrap sanity checks"
python3 scripts/validate_test_traceability.py
pytest tests/infrastructure -q

echo "Phase 1 bootstrap baseline is initialized."
