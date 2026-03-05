#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from app.billing.stripe_client import load_stripe_config, validate_no_hardcoded_prices

cfg = load_stripe_config()
print({"product_id": cfg.product_id, "price_id": cfg.price_id})
if not validate_no_hardcoded_prices(cfg):
    raise SystemExit("Stripe Product/Price IDs are invalid")
PY
