"""SLO model scaffolding for OPS-002."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SLO:
    name: str
    target: float


PHASE1_SLOS: list[SLO] = [
    SLO(name="availability", target=99.9),
    SLO(name="p95_latency_ms", target=300.0),
    SLO(name="error_rate_pct", target=0.5),
    SLO(name="ingest_success_pct", target=99.5),
]

SLO_REPORTING_RETENTION_DAYS = 90
SLA_LINKAGE = {
    "availability": "SLA-AVAIL-001",
    "p95_latency_ms": "SLA-LAT-001",
    "error_rate_pct": "SLA-ERR-001",
    "ingest_success_pct": "SLA-ING-001",
}


def error_budget(target: float) -> float:
    return max(100.0 - target, 0.0)
