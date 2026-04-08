# ChronosRefine Phase 5 Packet 5B Closeout Note

Status: Context-only closeout evidence note. This file does not alter canonical source-of-truth ordering in `AGENTS.md`.

## Packet 5B Scope

- Packet: `Packet 5B`
- Requirement focus: `FR-006`
- Candidate branch: `codex/phase5-packet5b-impl`
- Hosted closeout date: `2026-04-08`
- Shared hosted environment: `chronos_dev`
- Cloud Run service: `chronos-phase1-app`
- Final serving revision: `chronos-phase1-app-00062-hmn`

## Summary

Packet 5B is hosted-complete and closes global `FR-006`. The packet extends Packet 5A's approved-preview gate to public `POST /v1/jobs`, keeps Packet 5A preview-review and preview-launch behavior intact, preserves `/v1/jobs/estimate` billing behavior, and records the local plus hosted closeout evidence required to mark `FR-006` globally complete in `chronos_dev`.

Packet 5B intentionally changes the public generic launch contract for external clients. Bare legacy `/v1/jobs` payloads without `launch_context` are now rejected with `409 /problems/preview_approval_required`. The migration path is: save or fetch configuration again, generate and approve the current preview, then relaunch with the refreshed payload carrying `launch_context.source = approved_preview`.

## Verification Commands

Local validation:

```bash
python3 scripts/validate_test_traceability.py
./.venv/bin/python -m pytest tests/api/test_preview_sessions.py tests/api/test_async_processing.py tests/api/test_cost_estimation.py tests/api/test_endpoints.py tests/integration/test_preview_pipeline.py tests/integration/test_processing_launch_flow.py tests/integration/test_configuration_job_handoff.py tests/processing/test_preview_generation.py tests/processing/test_scene_detection.py tests/load/test_preview_performance.py -q
node web/node_modules/vitest/vitest.mjs run --config web/vitest.config.ts tests/ui/test_preview_modal.spec.ts tests/accessibility/test_preview_review_modal_a11y.spec.ts tests/ui/test_cost_estimate_modal.spec.ts
.agents/skills/spec-consistency-audit/scripts/audit_specs.sh /private/tmp/chronos_phase5_packet5b_impl
python3 scripts/ops/verify_cloud_run_runtime.py --service chronos-phase1-app --project chronos-dev-489301 --region us-central1
```

Hosted closeout probes:

```bash
./.venv/bin/python /tmp/packet5b_hosted_closeout.py --mode basic
./.venv/bin/python /tmp/packet5b_hosted_closeout.py --mode publish-fail
./.venv/bin/python /tmp/packet5b_hosted_closeout.py --mode retry-existing --preview-id <preview_id> --configuration-fingerprint <fingerprint>
./.venv/bin/python /tmp/packet5b_hosted_closeout.py --mode preview-latency
curl -s https://chronos-phase1-app-19961431854.us-central1.run.app/v1/metrics
curl -s https://chronos-phase1-app-19961431854.us-central1.run.app/v1/version
```

## Evidence Summary

### Local Validation

- `python3 scripts/validate_test_traceability.py`
  - Result: passed
- `.agents/skills/spec-consistency-audit/scripts/audit_specs.sh /private/tmp/chronos_phase5_packet5b_impl`
  - Result: passed
- Focused and broader Packet 5B backend suites
  - Result: passed
- Targeted Packet 5A/5B web and accessibility suites
  - Result: passed
- `python3 scripts/ops/verify_cloud_run_runtime.py --service chronos-phase1-app --project chronos-dev-489301 --region us-central1`
  - Result: passed on final serving revision

### Schema / Index Checkpoint

- Packet 5B added no schema migration.
- Packet 5A migration state through `0024` remained valid in `chronos_dev`.
- Owner-scoped upload lookup plus derived preview resolution indexes were confirmed sufficient for the new `/v1/jobs` preview-gate path, so no additive index-only migration was required.

### Hosted Packet 5B Smoke

- Final serving revision: `chronos-phase1-app-00062-hmn`
- Version endpoint:

```json
{"version":"0.2.0","build_sha":"3d7145c29ddea8691c480b0f543019dad3a5af4a","build_time":"2026-04-08T08:52:45Z"}
```

- Hosted proof:
  - `POST /v1/previews` returned `review_status = pending`
  - bare `POST /v1/jobs` without `launch_context` returned `409 /problems/preview_approval_required`
  - malformed `launch_context` returned `422`
  - refreshed approved payload launched successfully through `POST /v1/jobs`
  - repeated approved generic launch returned the same `job_id` (`e3f95bfe-1793-59c5-9579-ca265d173dc4`)
  - pre-5B saved payload without `launch_context` returned `409 /problems/preview_approval_required`
  - refreshed saved payload with approved preview returned `202` and queued job `44201c89-5754-5e04-88b1-a062d85f2722`
  - stale anti-replay returned `/problems/preview_stale`
  - cross-user preview review, preview launch, and generic `/v1/jobs` launch remained denied (`404`)
  - Packet 5A preview-launch route remained green:
    - before approval: `/problems/preview_approval_required`
    - after approval: queued job `76c91c37-0ee6-5101-8e3d-25e8077caf0d`
  - `/v1/jobs/estimate` accepted the shared request shape with and without `launch_context` and preserved billing behavior

### Publish-Failure Retry and Recovery

- Injected publish failure returned `/problems/launch_dispatch_failed`
- Target preview entered `launch_pending`
- Bound job id during the failure path: `d53bfe34-d68f-52ec-a888-8465f2647311`
- Retry after restoring the correct Pub/Sub topic reused the same `job_id` and advanced the preview to `launched`
- Final runtime gauges after recovery:
  - `preview_launch_pending_count = 0.0`
  - `preview_launch_pending_oldest_age_seconds = 0.0`
- Final stale `launch_pending` state older than five minutes: `0`

### Runtime Signals

- `/v1/metrics` on the final serving revision showed the expected Packet 5B rollout signals:
  - `chronos_job_runtime_events_total{event_type="preview_approval_required_jobs_launch"} 1`
  - `chronos_job_runtime_events_total{event_type="preview_launch_pending_stale"} 2`
  - `chronos_runtime_gauge{name="preview_launch_pending_count"} 0.0`
  - `chronos_runtime_gauge{name="preview_launch_pending_oldest_age_seconds"} 0.0`

### Hosted Preview Latency

- Smoke sample size: `6`
- `p50 = 0.8767s`
- `p95 = 0.9314s`
- `p99 = 0.9314s`
- `mean = 0.8807s`
- `max = 0.9314s`
- Result: within the canonical `<6s p95` guardrail

## Consumer Rollout Note

- This packet intentionally changes public `/v1/jobs` behavior for bare legacy launch clients.
- First-party UI remains unaffected because Packet 5A already routes launch through approved-preview flow.
- API clients still sending pre-5B saved payloads must:
  1. save or fetch the configuration again,
  2. generate and approve the current preview,
  3. relaunch with the refreshed payload that includes `launch_context`.

## Packet Status

- Packet 5A status: `hosted-complete`
- Packet 5B status: `hosted-complete`
- Global `FR-006` status: complete
- Phase 5 full-requirement count: `1/11`
