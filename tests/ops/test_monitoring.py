"""Maps to: OPS-001, OPS-002"""

from pathlib import Path

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


def test_monitoring_terraform_resources_declared() -> None:
    root = Path(__file__).resolve().parents[2]
    monitoring_tf = (root / "infra/terraform/monitoring.tf").read_text(encoding="utf-8")
    alerts_tf = (root / "infra/terraform/alerts.tf").read_text(encoding="utf-8")

    assert "google_monitoring_dashboard" in monitoring_tf
    assert "custom.googleapis.com" in monitoring_tf
    assert "google_monitoring_alert_policy" in alerts_tf
    assert "notification_channels" in alerts_tf
    assert "placeholder" not in monitoring_tf.lower()
    assert "placeholder" not in alerts_tf.lower()


def test_iam_terraform_resources_declared() -> None:
    root = Path(__file__).resolve().parents[2]
    iam_tf = (root / "infra/terraform/iam.tf").read_text(encoding="utf-8")

    assert "google_project_iam_member" in iam_tf
    assert "roles/logging.logWriter" in iam_tf
    assert "roles/monitoring.metricWriter" in iam_tf
    assert "roles/run.admin" in iam_tf
