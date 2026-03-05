"""Maps to: OPS-002"""

import json
import logging

import pytest

from app.observability.logging import JsonFormatter
from app.observability.slo import PHASE1_SLOS, SLA_LINKAGE, SLO_REPORTING_RETENTION_DAYS, error_budget


def test_json_formatter_outputs_json() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "hello", args=(), exc_info=None)
    payload = json.loads(formatter.format(record))
    assert payload["message"] == "hello"


def test_phase1_slo_definitions_exist() -> None:
    assert len(PHASE1_SLOS) == 4
    assert error_budget(99.9) == pytest.approx(0.1)
    assert SLO_REPORTING_RETENTION_DAYS == 90
    assert "availability" in SLA_LINKAGE
