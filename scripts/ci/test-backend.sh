#!/usr/bin/env bash
set -euo pipefail

pytest tests/infrastructure tests/database tests/auth tests/billing tests/ops -q
