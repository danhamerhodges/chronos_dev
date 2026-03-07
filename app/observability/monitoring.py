"""Monitoring payloads for /v1/metrics endpoint."""

from __future__ import annotations

from collections import defaultdict

from app.config import settings


_HTTP_REQUEST_COUNTS: dict[str, int] = defaultdict(int)
_ERA_DETECTION_COUNTS = {"requests": 0, "manual_overrides": 0}
_ERA_CONFIDENCE_SUM = 0.0
_ERA_LATENCY_SUM_MS = 0.0
_GEMINI_USAGE = {"api_calls": 0, "total_tokens": 0, "provider_fallbacks": 0}
_JOB_RUNTIME_COUNTS: dict[str, int] = defaultdict(int)
_SEGMENT_RETRY_COUNTS: dict[str, int] = defaultdict(int)
_SEGMENT_FAILURE_COUNTS: dict[str, int] = defaultdict(int)
_WEBHOOK_ATTEMPT_COUNTS: dict[str, int] = defaultdict(int)
_JOB_STAGE_TIMING_SUMS_MS: dict[str, int] = defaultdict(int)
_JOB_STAGE_TIMING_COUNTS: dict[str, int] = defaultdict(int)
_CACHE_EVENT_COUNTS: dict[str, int] = defaultdict(int)
_CACHE_LATENCY_SUMS_MS: dict[str, int] = defaultdict(int)
_GPU_EVENT_COUNTS: dict[str, int] = defaultdict(int)
_GPU_ALLOCATION_LATENCY_SUMS_MS: dict[str, int] = defaultdict(int)
_ALERT_DELIVERY_COUNTS: dict[str, int] = defaultdict(int)
_INCIDENT_COUNTS: dict[str, int] = defaultdict(int)
_RUNTIME_GAUGES: dict[str, float] = defaultdict(float)


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


def record_job_runtime_event(event_type: str) -> None:
    _JOB_RUNTIME_COUNTS[event_type] += 1


def record_segment_retry(error_classification: str) -> None:
    _SEGMENT_RETRY_COUNTS[error_classification] += 1


def record_segment_failure(error_classification: str) -> None:
    _SEGMENT_FAILURE_COUNTS[error_classification] += 1


def record_webhook_attempt(status: str) -> None:
    _WEBHOOK_ATTEMPT_COUNTS[status] += 1


def record_job_stage_timings(stage_timings: dict[str, int | None]) -> None:
    for stage, duration_ms in stage_timings.items():
        if duration_ms is None:
            continue
        _JOB_STAGE_TIMING_SUMS_MS[stage] += int(duration_ms)
        _JOB_STAGE_TIMING_COUNTS[stage] += 1


def record_cache_event(status: str, *, latency_ms: int | None = None) -> None:
    _CACHE_EVENT_COUNTS[status] += 1
    if latency_ms is not None:
        _CACHE_LATENCY_SUMS_MS[status] += int(latency_ms)


def record_gpu_allocation(*, gpu_type: str, warm: bool, latency_ms: int) -> None:
    mode = "warm" if warm else "cold"
    _GPU_EVENT_COUNTS[f"allocation:{gpu_type}:{mode}"] += 1
    _GPU_ALLOCATION_LATENCY_SUMS_MS[f"{gpu_type}:{mode}"] += int(latency_ms)


def record_runtime_snapshot(snapshot: dict[str, float | int]) -> None:
    for key, value in snapshot.items():
        _RUNTIME_GAUGES[key] = float(value)


def record_alert_delivery(*, route: str, severity: str, outcome: str) -> None:
    _ALERT_DELIVERY_COUNTS[f"{route}:{severity}:{outcome}"] += 1


def record_incident(*, severity: str, state: str) -> None:
    _INCIDENT_COUNTS[f"{severity}:{state}"] += 1


def record_slo_evaluation(
    *,
    compliant: bool,
    p95_ratio: float,
    degraded: bool,
    error_budget_burn_percent: float,
) -> None:
    _RUNTIME_GAUGES["slo_p95_ratio"] = float(p95_ratio)
    _RUNTIME_GAUGES["slo_compliant"] = 1.0 if compliant else 0.0
    _RUNTIME_GAUGES["slo_degraded"] = 1.0 if degraded else 0.0
    _RUNTIME_GAUGES["error_budget_burn_percent"] = float(error_budget_burn_percent)


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
    lines.extend(
        [
            f"# HELP {namespace}_job_runtime_events_total Total async job runtime events.",
            f"# TYPE {namespace}_job_runtime_events_total counter",
        ]
    )
    for event_type, count in sorted(_JOB_RUNTIME_COUNTS.items()):
        lines.append(f"{namespace}_job_runtime_events_total{{event_type=\"{event_type}\"}} {count}")
    lines.extend(
        [
            f"# HELP {namespace}_job_segment_retries_total Total segment retries by error class.",
            f"# TYPE {namespace}_job_segment_retries_total counter",
        ]
    )
    for error_classification, count in sorted(_SEGMENT_RETRY_COUNTS.items()):
        lines.append(
            f"{namespace}_job_segment_retries_total{{error_classification=\"{error_classification}\"}} {count}"
        )
    lines.extend(
        [
            f"# HELP {namespace}_job_segment_failures_total Total terminal segment failures by error class.",
            f"# TYPE {namespace}_job_segment_failures_total counter",
        ]
    )
    for error_classification, count in sorted(_SEGMENT_FAILURE_COUNTS.items()):
        lines.append(
            f"{namespace}_job_segment_failures_total{{error_classification=\"{error_classification}\"}} {count}"
        )
    lines.extend(
        [
            f"# HELP {namespace}_job_webhook_attempts_total Total webhook delivery attempts by status.",
            f"# TYPE {namespace}_job_webhook_attempts_total counter",
        ]
    )
    for webhook_status, count in sorted(_WEBHOOK_ATTEMPT_COUNTS.items()):
        lines.append(f"{namespace}_job_webhook_attempts_total{{status=\"{webhook_status}\"}} {count}")
    lines.extend(
        [
            f"# HELP {namespace}_job_stage_duration_ms_sum Sum of job stage durations in milliseconds.",
            f"# TYPE {namespace}_job_stage_duration_ms_sum counter",
        ]
    )
    for stage, duration_ms in sorted(_JOB_STAGE_TIMING_SUMS_MS.items()):
        lines.append(f"{namespace}_job_stage_duration_ms_sum{{stage=\"{stage}\"}} {duration_ms}")
    lines.extend(
        [
            f"# HELP {namespace}_job_stage_duration_count Total completed timing observations by stage.",
            f"# TYPE {namespace}_job_stage_duration_count counter",
        ]
    )
    for stage, count in sorted(_JOB_STAGE_TIMING_COUNTS.items()):
        lines.append(f"{namespace}_job_stage_duration_count{{stage=\"{stage}\"}} {count}")
    lines.extend(
        [
            f"# HELP {namespace}_segment_cache_events_total Total segment cache events by status.",
            f"# TYPE {namespace}_segment_cache_events_total counter",
        ]
    )
    for status, count in sorted(_CACHE_EVENT_COUNTS.items()):
        lines.append(f"{namespace}_segment_cache_events_total{{status=\"{status}\"}} {count}")
    lines.extend(
        [
            f"# HELP {namespace}_segment_cache_latency_ms_sum Sum of segment cache latencies in milliseconds.",
            f"# TYPE {namespace}_segment_cache_latency_ms_sum counter",
        ]
    )
    for status, latency_ms in sorted(_CACHE_LATENCY_SUMS_MS.items()):
        lines.append(f"{namespace}_segment_cache_latency_ms_sum{{status=\"{status}\"}} {latency_ms}")
    lines.extend(
        [
            f"# HELP {namespace}_gpu_events_total Total GPU pool events.",
            f"# TYPE {namespace}_gpu_events_total counter",
        ]
    )
    for event_key, count in sorted(_GPU_EVENT_COUNTS.items()):
        lines.append(f"{namespace}_gpu_events_total{{event=\"{event_key}\"}} {count}")
    lines.extend(
        [
            f"# HELP {namespace}_gpu_allocation_latency_ms_sum Sum of GPU allocation latencies.",
            f"# TYPE {namespace}_gpu_allocation_latency_ms_sum counter",
        ]
    )
    for mode_key, latency_ms in sorted(_GPU_ALLOCATION_LATENCY_SUMS_MS.items()):
        lines.append(f"{namespace}_gpu_allocation_latency_ms_sum{{mode=\"{mode_key}\"}} {latency_ms}")
    lines.extend(
        [
            f"# HELP {namespace}_alert_delivery_total Total alert deliveries by route, severity, and outcome.",
            f"# TYPE {namespace}_alert_delivery_total counter",
        ]
    )
    for alert_key, count in sorted(_ALERT_DELIVERY_COUNTS.items()):
        route, severity, outcome = alert_key.split(":", 2)
        lines.append(
            f"{namespace}_alert_delivery_total{{route=\"{route}\",severity=\"{severity}\",outcome=\"{outcome}\"}} {count}"
        )
    lines.extend(
        [
            f"# HELP {namespace}_incident_total Total incidents by severity and state.",
            f"# TYPE {namespace}_incident_total counter",
        ]
    )
    for incident_key, count in sorted(_INCIDENT_COUNTS.items()):
        severity, state = incident_key.split(":", 1)
        lines.append(f"{namespace}_incident_total{{severity=\"{severity}\",state=\"{state}\"}} {count}")
    lines.extend(
        [
            f"# HELP {namespace}_runtime_gauge Runtime gauges for Packet 3C control plane.",
            f"# TYPE {namespace}_runtime_gauge gauge",
        ]
    )
    for name, value in sorted(_RUNTIME_GAUGES.items()):
        lines.append(f"{namespace}_runtime_gauge{{name=\"{name}\"}} {value}")
    return "\n".join(lines) + "\n"


def alert_routes() -> dict[str, str]:
    return {
        "pagerduty": "configured" if settings.pagerduty_integration_key else "memory",
        "slack": "configured" if settings.slack_alert_webhook_url else "memory",
    }
