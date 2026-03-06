"""Maps to: ENG-001"""

from app.validation.schema_validation import validate_era_profile
from tests.helpers.phase2 import valid_era_profile


def test_schema_validation_p95_stays_under_100ms() -> None:
    latencies = []
    payload = valid_era_profile()
    for _ in range(200):
        result = validate_era_profile(payload)
        assert result.is_valid is True
        latencies.append(result.latency_ms)

    p95_index = max(int(len(latencies) * 0.95) - 1, 0)
    p95 = sorted(latencies)[p95_index]
    assert p95 < 100
