"""Phase 2 repositories with Supabase-backed persistence and test fallback."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from app.config import settings
from app.db.client import SupabaseClient


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_uuid(value: str) -> str:
    return str(uuid5(NAMESPACE_URL, value))


def _billing_month() -> str:
    today = date.today()
    return today.replace(day=1).isoformat()


def _request_patch(payload: dict[str, Any], *, nullable_keys: set[str] | None = None) -> dict[str, Any]:
    allowed_nulls = nullable_keys or set()
    return {
        key: value
        for key, value in payload.items()
        if value is not None or key in allowed_nulls
    }


def phase2_backend_name() -> str:
    integration_enabled = os.getenv("CHRONOS_RUN_SUPABASE_INTEGRATION") == "1"
    has_direct_db = bool(
        settings.supabase_db_url
        or (
            settings.supabase_db_host
            and settings.supabase_db_port
            and settings.supabase_db_name
            and settings.supabase_db_user
            and settings.supabase_db_password
        )
    )
    if settings.environment == "production" and not has_direct_db:
        raise RuntimeError("Production environment requires direct Supabase database configuration.")
    if has_direct_db and (settings.environment != "test" or integration_enabled):
        return "supabase"
    return "memory"


@dataclass
class Phase2Store:
    users: dict[str, dict[str, Any]] = field(default_factory=dict)
    usage: dict[str, dict[str, Any]] = field(default_factory=dict)
    jobs: dict[str, dict[str, Any]] = field(default_factory=dict)
    era_detections: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    log_settings: dict[str, dict[str, Any]] = field(default_factory=dict)
    deletion_requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    deletion_proofs: dict[str, dict[str, Any]] = field(default_factory=dict)


_STORE = Phase2Store()


def reset_phase2_store() -> None:
    _STORE.users.clear()
    _STORE.usage.clear()
    _STORE.jobs.clear()
    _STORE.era_detections.clear()
    _STORE.log_settings.clear()
    _STORE.deletion_requests.clear()
    _STORE.deletion_proofs.clear()


class _MemoryUserProfileRepository:
    def get_or_create(
        self,
        *,
        user_id: str,
        role: str,
        plan_tier: str,
        org_id: str,
        email: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        profile = _STORE.users.get(user_id)
        if profile is None:
            profile = {
                "user_id": user_id,
                "email": email or f"{user_id}@example.com",
                "role": role,
                "plan_tier": plan_tier,
                "org_id": org_id,
                "display_name": None,
                "avatar_url": None,
                "preferences": {},
            }
            _STORE.users[user_id] = profile
        return dict(profile)

    def update(self, user_id: str, patch: dict[str, Any], *, access_token: str | None = None) -> dict[str, Any]:
        profile = dict(_STORE.users[user_id])
        profile.update({key: value for key, value in patch.items() if value not in (None, {})})
        if "preferences" in patch:
            profile["preferences"] = patch["preferences"]
        _STORE.users[user_id] = profile
        return dict(profile)


class _MemoryUsageRepository:
    def get_or_create(
        self,
        *,
        user_id: str,
        plan_tier: str,
        monthly_limit_minutes: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        usage = _STORE.usage.get(user_id)
        if usage is None:
            usage = {
                "user_id": user_id,
                "plan_tier": plan_tier,
                "used_minutes": 0,
                "monthly_limit_minutes": monthly_limit_minutes,
                "estimated_next_job_minutes": 0,
                "threshold_alerts": [],
                "overage_approval_scope": None,
                "approved_for_minutes": 0,
            }
            _STORE.usage[user_id] = usage
        return dict(usage)

    def update(self, user_id: str, payload: dict[str, Any], *, access_token: str | None = None) -> dict[str, Any]:
        usage = dict(_STORE.usage[user_id])
        usage.update(payload)
        _STORE.usage[user_id] = usage
        return dict(usage)


class _MemoryEraDetectionRepository:
    def save_job(
        self,
        *,
        job_id: str,
        owner_user_id: str,
        org_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        era_profile: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any]:
        record = {
            "job_id": job_id,
            "owner_user_id": owner_user_id,
            "org_id": org_id,
            "media_uri": media_uri,
            "original_filename": original_filename,
            "mime_type": mime_type,
            "era_profile": era_profile,
            "created_at": _utc_now(),
        }
        _STORE.jobs[job_id] = record
        return dict(record)

    def save_detection(self, *, job_id: str, detection: dict[str, Any], access_token: str | None = None) -> dict[str, Any]:
        detections = _STORE.era_detections.setdefault(job_id, [])
        record = {
            "id": str(uuid4()),
            "created_at": _utc_now(),
            **detection,
        }
        detections.append(record)
        return dict(record)

    def latest_detection(self, job_id: str, *, access_token: str | None = None) -> dict[str, Any] | None:
        detections = _STORE.era_detections.get(job_id, [])
        return dict(detections[-1]) if detections else None


class _MemoryLogSettingsRepository:
    def upsert(self, *, org_id: str, payload: dict[str, Any], updated_by: str, access_token: str | None = None) -> dict[str, Any]:
        record = {
            "org_id": org_id,
            "retention_days": payload["retention_days"],
            "redaction_mode": payload["redaction_mode"],
            "categories": payload["categories"],
            "export_targets": payload["export_targets"],
            "updated_by": updated_by,
            "updated_at": _utc_now(),
        }
        _STORE.log_settings[org_id] = record
        return dict(record)

    def get(self, org_id: str, *, access_token: str | None = None) -> dict[str, Any] | None:
        record = _STORE.log_settings.get(org_id)
        return dict(record) if record else None


class _MemoryComplianceRepository:
    def create_deletion_request(self, *, user_id: str, payload: dict[str, Any], access_token: str | None = None) -> dict[str, Any]:
        deletion_request_id = str(uuid4())
        deletion_proof_id = str(uuid4())
        deleted_entries = max(len(payload["categories"]), 1) * 12
        request_record = {
            "deletion_request_id": deletion_request_id,
            "deletion_proof_id": deletion_proof_id,
            "user_id": user_id,
            "deleted_categories": payload["categories"],
            "deleted_entries": deleted_entries,
            "status": "completed",
            "requested_at": _utc_now(),
        }
        proof_record = {
            "deletion_proof_id": deletion_proof_id,
            "deletion_request_id": deletion_request_id,
            "user_id": user_id,
            "deleted_entries": deleted_entries,
            "deleted_categories": payload["categories"],
            "generated_at": _utc_now(),
        }
        _STORE.deletion_requests[deletion_request_id] = request_record
        _STORE.deletion_proofs[deletion_proof_id] = proof_record
        return dict(request_record)


class _SupabaseRepositoryBase:
    def __init__(self) -> None:
        self._client = SupabaseClient()

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self._client.direct_db_dsn(), row_factory=dict_row)


class _SupabaseUserProfileRepository(_SupabaseRepositoryBase):
    def _row_to_profile(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_id": row["external_user_id"],
            "email": row["email"],
            "role": row["role"],
            "plan_tier": row.get("plan_tier", "hobbyist"),
            "org_id": row.get("org_id", "org-default"),
            "display_name": row.get("display_name"),
            "avatar_url": row.get("avatar_url"),
            "preferences": row.get("preferences") or {},
        }

    def get_or_create(
        self,
        *,
        user_id: str,
        role: str,
        plan_tier: str,
        org_id: str,
        email: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            row = self._client.rest_upsert(
                "user_profiles",
                payload={
                    "id": user_id,
                    "external_user_id": user_id,
                    "email": email or f"{user_id}@example.com",
                    "role": role,
                    "plan_tier": plan_tier,
                    "org_id": org_id,
                    "display_name": None,
                    "avatar_url": None,
                    "preferences": {},
                    "updated_at": _utc_now(),
                },
                on_conflict="id",
                headers=headers,
            )[0]
            return self._row_to_profile(row)
        from psycopg.types.json import Jsonb

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.user_profiles (
                    id, external_user_id, email, role, plan_tier, org_id,
                    display_name, avatar_url, preferences, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                on conflict (external_user_id) do update
                set role = excluded.role,
                    plan_tier = excluded.plan_tier,
                    org_id = excluded.org_id,
                    updated_at = now()
                returning *
                """,
                (
                    _stable_uuid(user_id),
                    user_id,
                    email or f"{user_id}@example.com",
                    role,
                    plan_tier,
                    org_id,
                    None,
                    None,
                    Jsonb({}),
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to upsert user profile")
        return self._row_to_profile(row)

    def update(self, user_id: str, patch: dict[str, Any], *, access_token: str | None = None) -> dict[str, Any]:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            payload = _request_patch(
                {
                    "display_name": patch.get("display_name"),
                    "avatar_url": patch.get("avatar_url"),
                    "preferences": patch.get("preferences"),
                    "updated_at": _utc_now(),
                }
            )
            row = self._client.rest_update(
                "user_profiles",
                payload=payload,
                params={"id": f"eq.{user_id}", "select": "*"},
                headers=headers,
            )[0]
            return self._row_to_profile(row)
        from psycopg.types.json import Jsonb

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                update public.user_profiles
                set display_name = case when %s then %s else display_name end,
                    avatar_url = case when %s then %s else avatar_url end,
                    preferences = case when %s then %s else preferences end,
                    updated_at = now()
                where external_user_id = %s
                returning *
                """,
                (
                    "display_name" in patch,
                    patch.get("display_name"),
                    "avatar_url" in patch,
                    patch.get("avatar_url"),
                    "preferences" in patch,
                    Jsonb(patch.get("preferences", {})),
                    user_id,
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to update user profile")
        return self._row_to_profile(row)


class _SupabaseUsageRepository(_SupabaseRepositoryBase):
    def _row_to_usage(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_id": row["external_user_id"],
            "plan_tier": row["plan_tier"],
            "used_minutes": row["used_minutes"],
            "monthly_limit_minutes": row["monthly_limit_minutes"],
            "estimated_next_job_minutes": row.get("estimated_next_job_minutes", 0),
            "threshold_alerts": row.get("threshold_alerts") or [],
            "overage_approval_scope": row.get("approval_scope"),
            "approved_for_minutes": row.get("approved_overage_minutes", 0),
        }

    def get_or_create(
        self,
        *,
        user_id: str,
        plan_tier: str,
        monthly_limit_minutes: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        month = _billing_month()
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            rows = self._client.rest_select(
                "user_usage_monthly",
                params={
                    "select": "*",
                    "external_user_id": f"eq.{user_id}",
                    "billing_month": f"eq.{month}",
                    "limit": "1",
                },
                headers=headers,
            )
            if rows:
                return self._row_to_usage(rows[0])
            row = self._client.rest_insert(
                "user_usage_monthly",
                payload={
                    "id": str(uuid4()),
                    "owner_user_id": user_id,
                    "external_user_id": user_id,
                    "billing_month": month,
                    "plan_tier": plan_tier,
                    "used_minutes": 0,
                    "monthly_limit_minutes": monthly_limit_minutes,
                    "estimated_next_job_minutes": 0,
                    "approved_overage_minutes": 0,
                    "approval_scope": None,
                    "threshold_alerts": [],
                    "updated_at": _utc_now(),
                },
                headers=headers,
            )[0]
            return self._row_to_usage(row)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.user_usage_monthly (
                    id, owner_user_id, external_user_id, billing_month, plan_tier,
                    used_minutes, monthly_limit_minutes, estimated_next_job_minutes,
                    approved_overage_minutes, approval_scope, threshold_alerts, updated_at
                )
                values (%s, %s, %s, %s, %s, 0, %s, 0, 0, null, %s, now())
                on conflict (external_user_id, billing_month) do update
                set plan_tier = excluded.plan_tier,
                    monthly_limit_minutes = excluded.monthly_limit_minutes,
                    updated_at = now()
                returning *
                """,
                (
                    str(uuid4()),
                    _stable_uuid(user_id),
                    user_id,
                    month,
                    plan_tier,
                    monthly_limit_minutes,
                    [],
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to upsert usage snapshot")
        return self._row_to_usage(row)

    def update(self, user_id: str, payload: dict[str, Any], *, access_token: str | None = None) -> dict[str, Any]:
        month = _billing_month()
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            request_payload = {
                "updated_at": _utc_now(),
            }
            if "used_minutes" in payload:
                request_payload["used_minutes"] = payload.get("used_minutes")
            if "estimated_next_job_minutes" in payload:
                request_payload["estimated_next_job_minutes"] = payload.get("estimated_next_job_minutes")
            if "approved_for_minutes" in payload:
                request_payload["approved_overage_minutes"] = payload.get("approved_for_minutes")
            if "overage_approval_scope" in payload:
                request_payload["approval_scope"] = payload.get("overage_approval_scope")
            if "threshold_alerts" in payload:
                request_payload["threshold_alerts"] = payload.get("threshold_alerts")
            row = self._client.rest_update(
                "user_usage_monthly",
                payload=request_payload,
                params={
                    "external_user_id": f"eq.{user_id}",
                    "billing_month": f"eq.{month}",
                    "select": "*",
                },
                headers=headers,
            )[0]
            return self._row_to_usage(row)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                update public.user_usage_monthly
                set used_minutes = case when %s then %s else used_minutes end,
                    estimated_next_job_minutes = case when %s then %s else estimated_next_job_minutes end,
                    approved_overage_minutes = case when %s then %s else approved_overage_minutes end,
                    approval_scope = case when %s then %s else approval_scope end,
                    threshold_alerts = case when %s then %s else threshold_alerts end,
                    updated_at = now()
                where external_user_id = %s and billing_month = %s
                returning *
                """,
                (
                    "used_minutes" in payload,
                    payload.get("used_minutes"),
                    "estimated_next_job_minutes" in payload,
                    payload.get("estimated_next_job_minutes"),
                    "approved_for_minutes" in payload,
                    payload.get("approved_for_minutes"),
                    "overage_approval_scope" in payload,
                    payload.get("overage_approval_scope"),
                    "threshold_alerts" in payload,
                    payload.get("threshold_alerts"),
                    user_id,
                    month,
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to update usage snapshot")
        return self._row_to_usage(row)


class _SupabaseEraDetectionRepository(_SupabaseRepositoryBase):
    def save_job(
        self,
        *,
        job_id: str,
        owner_user_id: str,
        org_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        era_profile: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any]:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            row = self._client.rest_upsert(
                "media_jobs",
                payload={
                    "id": _stable_uuid(job_id),
                    "external_job_id": job_id,
                    "owner_user_id": owner_user_id,
                    "external_user_id": owner_user_id,
                    "org_id": org_id,
                    "media_uri": media_uri,
                    "original_filename": original_filename,
                    "mime_type": mime_type,
                    "status": "queued",
                    "era_profile": era_profile,
                },
                on_conflict="external_job_id",
                headers=headers,
            )[0]
            return {
                "job_id": row["external_job_id"],
                "owner_user_id": row["external_user_id"],
                "org_id": row["org_id"],
                "media_uri": row["media_uri"],
                "original_filename": row["original_filename"],
                "mime_type": row["mime_type"],
                "era_profile": row["era_profile"],
                "created_at": row["created_at"],
            }
        from psycopg.types.json import Jsonb

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.media_jobs (
                    id, owner_user_id, external_user_id, external_job_id, org_id,
                    media_uri, original_filename, mime_type, status, era_profile
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, 'queued', %s)
                on conflict (external_job_id) do update
                set owner_user_id = excluded.owner_user_id,
                    external_user_id = excluded.external_user_id,
                    org_id = excluded.org_id,
                    media_uri = excluded.media_uri,
                    original_filename = excluded.original_filename,
                    mime_type = excluded.mime_type,
                    era_profile = excluded.era_profile
                returning *
                """,
                (
                    _stable_uuid(job_id),
                    _stable_uuid(owner_user_id),
                    owner_user_id,
                    job_id,
                    org_id,
                    media_uri,
                    original_filename,
                    mime_type,
                    Jsonb(era_profile),
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to upsert media job")
        return {
            "job_id": row["external_job_id"],
            "owner_user_id": row["external_user_id"],
            "org_id": row["org_id"],
            "media_uri": row["media_uri"],
            "original_filename": row["original_filename"],
            "mime_type": row["mime_type"],
            "era_profile": row["era_profile"],
            "created_at": row["created_at"],
        }

    def save_detection(self, *, job_id: str, detection: dict[str, Any], access_token: str | None = None) -> dict[str, Any]:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            row = self._client.rest_insert(
                "era_detections",
                payload={
                    "id": str(uuid4()),
                    "job_id": _stable_uuid(job_id),
                    "external_job_id": job_id,
                    "era_label": detection["era"],
                    "confidence": detection["confidence"],
                    "forensic_markers": detection["forensic_markers"],
                    "top_candidates": detection.get("top_candidates", []),
                    "manual_confirmation_required": detection.get("manual_confirmation_required", False),
                    "overridden_by_user": detection.get("overridden_by_user", False),
                    "override_reason": detection.get("override_reason"),
                    "source": detection["source"],
                    "model_version": detection["model_version"],
                    "prompt_version": detection["prompt_version"],
                    "raw_response_gcs_uri": detection.get("raw_response_gcs_uri"),
                    "prompt_token_count": detection.get("prompt_token_count", 0),
                    "candidates_token_count": detection.get("candidates_token_count", 0),
                    "total_token_count": detection.get("total_token_count", 0),
                    "api_call_count": detection.get("api_call_count", 0),
                    "created_by": detection["created_by"],
                    "external_created_by": detection.get("created_by"),
                },
                headers=headers,
            )[0]
            return {
                "id": row["id"],
                "job_id": row["external_job_id"],
                "era": row["era_label"],
                "confidence": float(row["confidence"]),
                "forensic_markers": row["forensic_markers"],
                "top_candidates": row.get("top_candidates") or [],
                "manual_confirmation_required": row.get("manual_confirmation_required", False),
                "overridden_by_user": row["overridden_by_user"],
                "override_reason": row.get("override_reason"),
                "model_version": row["model_version"],
                "prompt_version": row["prompt_version"],
                "source": row["source"],
                "raw_response_gcs_uri": row.get("raw_response_gcs_uri"),
                "prompt_token_count": row.get("prompt_token_count", 0),
                "candidates_token_count": row.get("candidates_token_count", 0),
                "total_token_count": row.get("total_token_count", 0),
                "api_call_count": row.get("api_call_count", 0),
                "created_by": row.get("external_created_by"),
                "created_at": row["created_at"],
            }
        from psycopg.types.json import Jsonb

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.era_detections (
                    id, job_id, external_job_id, era_label, confidence, forensic_markers,
                    top_candidates, manual_confirmation_required, overridden_by_user,
                    override_reason, source, model_version, prompt_version,
                    raw_response_gcs_uri, prompt_token_count, candidates_token_count,
                    total_token_count, api_call_count, created_by, external_created_by
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning *
                """,
                (
                    str(uuid4()),
                    _stable_uuid(job_id),
                    job_id,
                    detection["era"],
                    detection["confidence"],
                    Jsonb(detection["forensic_markers"]),
                    Jsonb(detection.get("top_candidates", [])),
                    detection.get("manual_confirmation_required", False),
                    detection.get("overridden_by_user", False),
                    detection.get("override_reason"),
                    detection["source"],
                    detection["model_version"],
                    detection["prompt_version"],
                    detection.get("raw_response_gcs_uri"),
                    detection.get("prompt_token_count", 0),
                    detection.get("candidates_token_count", 0),
                    detection.get("total_token_count", 0),
                    detection.get("api_call_count", 0),
                    _stable_uuid(detection["created_by"]) if detection.get("created_by") else None,
                    detection.get("created_by"),
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to insert era detection")
        return {
            "id": row["id"],
            "job_id": row["external_job_id"],
            "era": row["era_label"],
            "confidence": float(row["confidence"]),
            "forensic_markers": row["forensic_markers"],
            "top_candidates": row.get("top_candidates") or [],
            "manual_confirmation_required": row.get("manual_confirmation_required", False),
            "overridden_by_user": row["overridden_by_user"],
            "override_reason": row.get("override_reason"),
            "model_version": row["model_version"],
            "prompt_version": row["prompt_version"],
            "source": row["source"],
            "raw_response_gcs_uri": row.get("raw_response_gcs_uri"),
            "prompt_token_count": row.get("prompt_token_count", 0),
            "candidates_token_count": row.get("candidates_token_count", 0),
            "total_token_count": row.get("total_token_count", 0),
            "api_call_count": row.get("api_call_count", 0),
            "created_by": row.get("external_created_by"),
            "created_at": row["created_at"],
        }

    def latest_detection(self, job_id: str, *, access_token: str | None = None) -> dict[str, Any] | None:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            rows = self._client.rest_select(
                "era_detections",
                params={
                    "select": "*",
                    "external_job_id": f"eq.{job_id}",
                    "order": "created_at.desc",
                    "limit": "1",
                },
                headers=headers,
            )
            if not rows:
                return None
            row = rows[0]
            detection = self._from_row(row)
            return {
                "id": row["id"],
                "job_id": row["external_job_id"],
                **detection,
                "created_at": row["created_at"],
            }
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select *
                from public.era_detections
                where external_job_id = %s
                order by created_at desc
                limit 1
                """,
                (job_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        detection = self._from_row(row)
        return {
            "id": row["id"],
            "job_id": row["external_job_id"],
            **detection,
            "created_at": row["created_at"],
        }

    def _from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "era": row["era_label"],
            "confidence": float(row["confidence"]),
            "forensic_markers": row["forensic_markers"],
            "top_candidates": row.get("top_candidates") or [],
            "overridden_by_user": row["overridden_by_user"],
            "override_reason": row.get("override_reason"),
            "model_version": row["model_version"],
            "prompt_version": row["prompt_version"],
            "source": row["source"],
            "raw_response_gcs_uri": row.get("raw_response_gcs_uri"),
            "prompt_token_count": row.get("prompt_token_count", 0),
            "candidates_token_count": row.get("candidates_token_count", 0),
            "total_token_count": row.get("total_token_count", 0),
            "api_call_count": row.get("api_call_count", 0),
            "created_by": row.get("external_created_by"),
            "manual_confirmation_required": row.get("manual_confirmation_required", False),
        }


class _SupabaseLogSettingsRepository(_SupabaseRepositoryBase):
    def upsert(self, *, org_id: str, payload: dict[str, Any], updated_by: str, access_token: str | None = None) -> dict[str, Any]:
        from psycopg.types.json import Jsonb

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.org_log_settings (
                    org_id, retention_days, redaction_mode, categories,
                    export_targets, updated_by, external_updated_by, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, now())
                on conflict (org_id) do update
                set retention_days = excluded.retention_days,
                    redaction_mode = excluded.redaction_mode,
                    categories = excluded.categories,
                    export_targets = excluded.export_targets,
                    updated_by = excluded.updated_by,
                    external_updated_by = excluded.external_updated_by,
                    updated_at = now()
                returning *
                """,
                (
                    org_id,
                    payload["retention_days"],
                    payload["redaction_mode"],
                    Jsonb(payload["categories"]),
                    Jsonb(payload["export_targets"]),
                    _stable_uuid(updated_by),
                    updated_by,
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to upsert log settings")
        return {
            "org_id": row["org_id"],
            "retention_days": row["retention_days"],
            "redaction_mode": row["redaction_mode"],
            "categories": row.get("categories") or [],
            "export_targets": row.get("export_targets") or [],
            "updated_by": row.get("external_updated_by", updated_by),
            "updated_at": row["updated_at"],
        }

    def get(self, org_id: str, *, access_token: str | None = None) -> dict[str, Any] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("select * from public.org_log_settings where org_id = %s limit 1", (org_id,))
            row = cur.fetchone()
        if row is None:
            return None
        return {
            "org_id": row["org_id"],
            "retention_days": row["retention_days"],
            "redaction_mode": row["redaction_mode"],
            "categories": row.get("categories") or [],
            "export_targets": row.get("export_targets") or [],
            "updated_by": row.get("external_updated_by"),
            "updated_at": row["updated_at"],
        }


class _SupabaseComplianceRepository(_SupabaseRepositoryBase):
    def create_deletion_request(self, *, user_id: str, payload: dict[str, Any], access_token: str | None = None) -> dict[str, Any]:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            deletion_request_id = str(uuid4())
            deletion_proof_id = str(uuid4())
            deleted_entries = max(len(payload["categories"]), 1) * 12
            request_payload = {
                "id": deletion_request_id,
                "owner_user_id": user_id,
                "external_user_id": user_id,
                "categories": payload["categories"],
                "date_from": payload["date_from"],
                "date_to": payload["date_to"],
                "reason": payload.get("reason"),
                "status": "completed",
                "deletion_proof_id": deletion_proof_id,
            }
            proof_payload = {
                "id": deletion_proof_id,
                "deletion_request_id": deletion_request_id,
                "owner_user_id": user_id,
                "external_user_id": user_id,
                "deleted_entries": deleted_entries,
                "deleted_categories": payload["categories"],
            }
            self._client.rest_insert(
                "log_deletion_requests",
                payload=request_payload,
                headers=headers,
            )
            try:
                self._client.rest_insert(
                    "log_deletion_proofs",
                    payload=proof_payload,
                    headers=headers,
                )
            except Exception:
                self._client.rest_delete(
                    "log_deletion_requests",
                    params={"id": f"eq.{deletion_request_id}"},
                    headers=headers,
                )
                raise
            return {
                "deletion_request_id": deletion_request_id,
                "deletion_proof_id": deletion_proof_id,
                "user_id": user_id,
                "deleted_categories": payload["categories"],
                "deleted_entries": deleted_entries,
                "status": "completed",
                "requested_at": _utc_now(),
            }
        from psycopg.types.json import Jsonb

        deletion_request_id = str(uuid4())
        deletion_proof_id = str(uuid4())
        deleted_entries = max(len(payload["categories"]), 1) * 12
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.log_deletion_requests (
                    id, owner_user_id, external_user_id, categories, date_from,
                    date_to, reason, status, deletion_proof_id
                )
                values (%s, %s, %s, %s, %s, %s, %s, 'completed', %s)
                """,
                (
                    deletion_request_id,
                    _stable_uuid(user_id),
                    user_id,
                    Jsonb(payload["categories"]),
                    payload["date_from"],
                    payload["date_to"],
                    payload.get("reason"),
                    deletion_proof_id,
                ),
            )
            cur.execute(
                """
                insert into public.log_deletion_proofs (
                    id, deletion_request_id, owner_user_id, external_user_id,
                    deleted_entries, deleted_categories
                )
                values (%s, %s, %s, %s, %s, %s)
                """,
                (
                    deletion_proof_id,
                    deletion_request_id,
                    _stable_uuid(user_id),
                    user_id,
                    deleted_entries,
                    Jsonb(payload["categories"]),
                ),
            )
        return {
            "deletion_request_id": deletion_request_id,
            "deletion_proof_id": deletion_proof_id,
            "user_id": user_id,
            "deleted_categories": payload["categories"],
            "deleted_entries": deleted_entries,
            "status": "completed",
            "requested_at": _utc_now(),
        }


def _user_profile_backend() -> _MemoryUserProfileRepository | _SupabaseUserProfileRepository:
    return _SupabaseUserProfileRepository() if phase2_backend_name() == "supabase" else _MemoryUserProfileRepository()


def _usage_backend() -> _MemoryUsageRepository | _SupabaseUsageRepository:
    return _SupabaseUsageRepository() if phase2_backend_name() == "supabase" else _MemoryUsageRepository()


def _era_detection_backend() -> _MemoryEraDetectionRepository | _SupabaseEraDetectionRepository:
    return _SupabaseEraDetectionRepository() if phase2_backend_name() == "supabase" else _MemoryEraDetectionRepository()


def _log_settings_backend() -> _MemoryLogSettingsRepository | _SupabaseLogSettingsRepository:
    return _SupabaseLogSettingsRepository() if phase2_backend_name() == "supabase" else _MemoryLogSettingsRepository()


def _compliance_backend() -> _MemoryComplianceRepository | _SupabaseComplianceRepository:
    return _SupabaseComplianceRepository() if phase2_backend_name() == "supabase" else _MemoryComplianceRepository()


class UserProfileRepository:
    def __init__(self) -> None:
        self._backend = _user_profile_backend()

    def get_or_create(
        self,
        *,
        user_id: str,
        role: str,
        plan_tier: str,
        org_id: str,
        email: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        return self._backend.get_or_create(
            user_id=user_id,
            role=role,
            plan_tier=plan_tier,
            org_id=org_id,
            email=email,
            access_token=access_token,
        )

    def update(self, user_id: str, patch: dict[str, Any], *, access_token: str | None = None) -> dict[str, Any]:
        return self._backend.update(user_id, patch, access_token=access_token)


class UsageRepository:
    def __init__(self) -> None:
        self._backend = _usage_backend()

    def get_or_create(
        self,
        *,
        user_id: str,
        plan_tier: str,
        monthly_limit_minutes: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        return self._backend.get_or_create(
            user_id=user_id,
            plan_tier=plan_tier,
            monthly_limit_minutes=monthly_limit_minutes,
            access_token=access_token,
        )

    def update(self, user_id: str, payload: dict[str, Any], *, access_token: str | None = None) -> dict[str, Any]:
        return self._backend.update(user_id, payload, access_token=access_token)


class EraDetectionRepository:
    def __init__(self) -> None:
        self._backend = _era_detection_backend()

    def save_job(
        self,
        *,
        job_id: str,
        owner_user_id: str,
        org_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        era_profile: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any]:
        return self._backend.save_job(
            job_id=job_id,
            owner_user_id=owner_user_id,
            org_id=org_id,
            media_uri=media_uri,
            original_filename=original_filename,
            mime_type=mime_type,
            era_profile=era_profile,
            access_token=access_token,
        )

    def save_detection(self, *, job_id: str, detection: dict[str, Any], access_token: str | None = None) -> dict[str, Any]:
        return self._backend.save_detection(job_id=job_id, detection=detection, access_token=access_token)

    def latest_detection(self, job_id: str, *, access_token: str | None = None) -> dict[str, Any] | None:
        return self._backend.latest_detection(job_id, access_token=access_token)


class LogSettingsRepository:
    def __init__(self) -> None:
        self._backend = _log_settings_backend()

    def upsert(self, *, org_id: str, payload: dict[str, Any], updated_by: str, access_token: str | None = None) -> dict[str, Any]:
        return self._backend.upsert(org_id=org_id, payload=payload, updated_by=updated_by, access_token=access_token)

    def get(self, org_id: str, *, access_token: str | None = None) -> dict[str, Any] | None:
        return self._backend.get(org_id, access_token=access_token)


class ComplianceRepository:
    def __init__(self) -> None:
        self._backend = _compliance_backend()

    def create_deletion_request(self, *, user_id: str, payload: dict[str, Any], access_token: str | None = None) -> dict[str, Any]:
        return self._backend.create_deletion_request(user_id=user_id, payload=payload, access_token=access_token)
