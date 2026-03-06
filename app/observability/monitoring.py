"""Monitoring payloads for /v1/metrics endpoint."""

from __future__ import annotations

from collections import defaultdict


_HTTP_REQUEST_COUNTS: dict[str, int] = defaultdict(int)
_ERA_DETECTION_COUNTS = {"requests": 0, "manual_overrides": 0}
_ERA_CONFIDENCE_SUM = 0.0
_ERA_LATENCY_SUM_MS = 0.0
_GEMINI_USAGE = {"api_calls": 0, "total_tokens": 0, "provider_fallbacks": 0}


def record_http_request(route: str) -> None:
    _HTTP_REQUEST_COUNTS[route] += 1


def record_era_detection(
    *,
    latency_ms: float,
    confidence: float,
    manual_override: bool,
    api_calls: int = 0,
    total_tokens: int = 0,
    provider_fallback: bool = False,
) -> None:
    global _ERA_CONFIDENCE_SUM, _ERA_LATENCY_SUM_MS
    _ERA_DETECTION_COUNTS["requests"] += 1
    if manual_override:
        _ERA_DETECTION_COUNTS["manual_overrides"] += 1
    _ERA_CONFIDENCE_SUM += confidence
    _ERA_LATENCY_SUM_MS += latency_ms
    _GEMINI_USAGE["api_calls"] += api_calls
    _GEMINI_USAGE["total_tokens"] += total_tokens
    if provider_fallback:
        _GEMINI_USAGE["provider_fallbacks"] += 1


def metrics_payload(namespace: str) -> str:
    lines = [
        f"# HELP {namespace}_service_up Service health status.",
        f"# TYPE {namespace}_service_up gauge",
        f"{namespace}_service_up 1",
        f"# HELP {namespace}_http_requests_total Total HTTP requests.",
        f"# TYPE {namespace}_http_requests_total counter",
    ]
    for route, count in sorted(_HTTP_REQUEST_COUNTS.items() or {"/health": 1}.items()):
        lines.append(f"{namespace}_http_requests_total{{route=\"{route}\"}} {count}")
    lines.extend(
        [
            f"# HELP {namespace}_era_detection_requests_total Total era-detection requests.",
            f"# TYPE {namespace}_era_detection_requests_total counter",
            f"{namespace}_era_detection_requests_total {_ERA_DETECTION_COUNTS['requests']}",
            f"# HELP {namespace}_era_detection_manual_overrides_total Total manual era overrides.",
            f"# TYPE {namespace}_era_detection_manual_overrides_total counter",
            f"{namespace}_era_detection_manual_overrides_total {_ERA_DETECTION_COUNTS['manual_overrides']}",
            f"# HELP {namespace}_era_detection_confidence_sum Sum of era-detection confidences.",
            f"# TYPE {namespace}_era_detection_confidence_sum gauge",
            f"{namespace}_era_detection_confidence_sum {_ERA_CONFIDENCE_SUM:.2f}",
            f"# HELP {namespace}_era_detection_latency_ms_sum Sum of era-detection latencies in milliseconds.",
            f"# TYPE {namespace}_era_detection_latency_ms_sum gauge",
            f"{namespace}_era_detection_latency_ms_sum {_ERA_LATENCY_SUM_MS:.2f}",
            f"# HELP {namespace}_gemini_api_calls_total Total Gemini API calls tracked for era detection.",
            f"# TYPE {namespace}_gemini_api_calls_total counter",
            f"{namespace}_gemini_api_calls_total {_GEMINI_USAGE['api_calls']}",
            f"# HELP {namespace}_gemini_tokens_total Total Gemini tokens tracked for era detection.",
            f"# TYPE {namespace}_gemini_tokens_total counter",
            f"{namespace}_gemini_tokens_total {_GEMINI_USAGE['total_tokens']}",
            f"# HELP {namespace}_gemini_provider_fallbacks_total Total era-detection provider fallbacks.",
            f"# TYPE {namespace}_gemini_provider_fallbacks_total counter",
            f"{namespace}_gemini_provider_fallbacks_total {_GEMINI_USAGE['provider_fallbacks']}",
        ]
    )
    return "\n".join(lines) + "\n"


def alert_routes() -> dict[str, str]:
    return {
        "pagerduty": "configured-via-env",
        "slack": "configured-via-env",
    }
