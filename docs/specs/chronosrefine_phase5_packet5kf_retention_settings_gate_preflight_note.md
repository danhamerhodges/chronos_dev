# ChronosRefine Phase 5 Packet 5K-F Retention Settings Gate Preflight Note

Status: Packet 5K-F implements the missing `DoD-SEC-005-10` retention settings API/UI gate and records durable approval-evidence preflight criteria. This packet does not close global `SEC-005`, does not record compliance approval, does not record two-engineer approval, and does not advance Phase 5 tracker counts.

- Packet: `Packet 5K-F`
- Parent packets: `Packet 5K-E3`, `Packet 5K-E4`, `Packet 5K-E5`
- Requirement focus: `SEC-005` Transformation Manifest Retention
- Phase 5 status: remains `2/11` full requirements complete
- Global `SEC-005` status: remains open

## Implementation Scope

Packet 5K-F adds the missing configuration surface for Museum transformation manifest retention:

1. API: `GET /v1/orgs/{org_id}/settings/retention` readback plus `PATCH /v1/orgs/{org_id}/settings/retention` updates
2. Web UI: top-level `Settings` action with `Settings > Data Retention` modal
3. Persistence: user-scoped REST write path for `org_data_retention_settings` when the API supplies an end-user JWT
4. RLS: migration `0028_phase5_sec005_retention_settings_rls.sql` grants authenticated same-org Museum admin/platform-admin access for select/insert/update
5. Tests: backend API, repository/RLS migration checks, and rendered UI coverage for Museum admin save and disabled non-admin access

## SEC-005 Evidence Boundary

Packet 5K-F does not change the Packet 5K-E3 lifecycle evidence model.

- GCS Object Lifecycle Management deletion may use the approved compensating evidence model when Cloud Audit Logs cannot emit the lifecycle action.
- Cloud Audit Logs remain required for emitted user/API-driven object create/read/write/delete operations.
- The compensating lifecycle evidence model cannot satisfy user/API-driven delete audit-log obligations.

## Remaining Gates Before SEC-005 Closeout

Global `SEC-005` remains open until a follow-up closeout packet records all of the following:

1. Packet 5K-F API/UI test evidence passing on the candidate branch.
2. Hosted/runtime evidence for the retention settings API/UI gate if closeout policy requires hosted proof.
3. Durable compliance approval evidence with reviewer/team identity, date, reviewed evidence bundle, decision, residual risk, and repo-safe artifact or PR-review link.
4. Durable two-engineer approval evidence with two distinct reviewers, date, reviewed evidence bundle, decision, and repo-safe artifact or PR-review link.
5. Matrix and implementation-plan tracker movement in the same packet that records final approval evidence.

Until those records exist, `SEC-005` remains open and Phase 5 remains `2/11` full requirements complete.

Recommended next loop after merge: `Packet 5K-G` durable compliance and two-engineer approval evidence capture, stopping before closeout if approval records are incomplete.
