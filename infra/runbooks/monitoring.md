# Monitoring Runbook

- Validate `/health` and `/v1/metrics` endpoints.
- Confirm dashboard data freshness and alert channel health.
- Confirm `queue_depth`, `desired_warm_instances`, `active_warm_instances`, `busy_instances`, `segment_cache_events_total`, `gpu_allocation_latency_ms_sum`, and `incident_total` metrics are present.
- Validate `/v1/ops/runtime` for alert routes, warm-pool state, and open incident records.
- Validate PagerDuty and Slack escalation paths quarterly.
- Review monthly error-budget burn and processing-time p95 ratio after each load/performance run.
