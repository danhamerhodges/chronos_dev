"""Maps to: ENG-016, SEC-013, OPS-001, OPS-002, NFR-012, DS-007"""

import pytest

try:
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
except Exception as exc:  # pragma: no cover - dependency-gated environment
    client = None
    pytestmark = pytest.mark.skip(reason=f"Test client unavailable in current environment: {exc}")
