"""Maps to: ENG-016, SEC-013, OPS-001, OPS-002, NFR-012, DS-007"""

from pathlib import Path


EXPECTED_PATHS = [
    "app/main.py",
    "app/api/metrics.py",
    "app/auth/supabase_auth.py",
    "app/db/client.py",
    "app/billing/stripe_client.py",
    "app/observability/monitoring.py",
    "web/src/styles/tokens.css",
    "web/src/components/Button.tsx",
    "infra/terraform/main.tf",
    "supabase/migrations/0001_init_schema.sql",
    "scripts/validate_test_traceability.py",
]


def test_phase1_structure_exists() -> None:
    root = Path(__file__).resolve().parents[2]
    missing = [p for p in EXPECTED_PATHS if not (root / p).exists()]
    assert not missing, f"Missing expected paths: {missing}"
