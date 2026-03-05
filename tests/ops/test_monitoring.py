"""Maps to: OPS-001, OPS-002"""

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from app.main import app
from app.observability.monitoring import alert_routes


def test_metrics_endpoint_prometheus_format() -> None:
    client = TestClient(app)
    resp = client.get("/v1/metrics")
    assert resp.status_code == 200
    assert "# TYPE" in resp.text
    assert "service_up" in resp.text


def test_alert_routes_declared() -> None:
    routes = alert_routes()
    assert routes["pagerduty"] == "configured-via-env"
    assert routes["slack"] == "configured-via-env"
