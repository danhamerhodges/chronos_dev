"""Monitoring payloads for /v1/metrics endpoint."""

from __future__ import annotations


def metrics_payload(namespace: str) -> str:
    lines = [
        f"# HELP {namespace}_service_up Service health status.",
        f"# TYPE {namespace}_service_up gauge",
        f"{namespace}_service_up 1",
        f"# HELP {namespace}_http_requests_total Total HTTP requests.",
        f"# TYPE {namespace}_http_requests_total counter",
        f"{namespace}_http_requests_total{{route=\"/health\"}} 1",
    ]
    return "\n".join(lines) + "\n"


def alert_routes() -> dict[str, str]:
    return {
        "pagerduty": "configured-via-env",
        "slack": "configured-via-env",
    }
