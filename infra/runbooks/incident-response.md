# Incident Response Runbook

## Severity Levels

- `P0`: Data loss, security incident, or total outage. Immediate escalation.
- `P1`: Museum SLA breach, sustained processing-time SLO breach, or GPU pool exhaustion blocking jobs. Escalate within 15 minutes.
- `P2`: Partial degradation such as Redis cache degraded mode or rising queue depth. Escalate within 1 hour.
- `P3`: Warning-only regressions and non-customer-facing ops drift.

## Immediate Response

1. Declare severity, incident owner, and incident key in PagerDuty and the tracker.
2. Capture blast radius, impacted requirements/SLOs, and current queue depth from `/v1/ops/runtime` and `/v1/metrics`.
3. Classify the dominant failure mode: `gpu-pool-exhaustion`, `processing-time-slo`, `processing-time-regression`, `redis-cache-degraded`, or `api-outage`.
4. Mitigate:
   - GPU pool exhaustion: reconcile warm pool, confirm worker lease churn, and validate dispatch backlog.
   - Redis degraded: verify bypass mode, confirm jobs continue, and restore cache connectivity.
   - SLO breach/regression: confirm queue wait, allocation latency, cache hit rate, and stage timing regressions.
5. Update status page and customer communication for `P0/P1` incidents.

## Closure

- Record `opened_at`, `acknowledged_at`, and `resolved_at`.
- Link the incident record to the issue tracker and runbook key.
- Schedule a postmortem within 5 business days for `P0/P1`.
- Review MTTR, MTTD, and incident frequency in the monthly ops review.
