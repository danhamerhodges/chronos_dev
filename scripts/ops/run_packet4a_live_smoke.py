#!/usr/bin/env python3
"""Opt-in live smoke and staging latency probe for Packet 4A uploads."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, replace
from datetime import date, datetime
import json
import math
import os
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

import httpx
import psycopg
from psycopg.rows import dict_row
from fastapi.testclient import TestClient

from app import config as app_config
from app.api import dependencies as api_dependencies
from app.auth.supabase_auth import SupabaseAuthService
from app.db.client import SupabaseClient
from app.db.phase2_store import _STORE, phase2_backend_name
from app.main import app


class LiveSmokePrerequisiteError(RuntimeError):
    """Raised when an opt-in live smoke cannot run because env prerequisites are missing."""


class LiveSmokeExecutionError(RuntimeError):
    """Raised when a live smoke assertion fails."""


@dataclass(frozen=True)
class ActorContext:
    headers: dict[str, str]
    user_id: str
    org_id: str


_LIVE_UPLOAD_SIZE_BYTES = 512 * 1024
_LIVE_CHUNK_SIZE_BYTES = 256 * 1024
_EVIDENCE_DIR = Path(".tmp/packet4a")
_SECONDARY_PREREQ_MESSAGE = (
    "Supabase-backed Packet 4A smoke requires explicit secondary-user credentials. "
    "Set CHRONOS_TEST_SECONDARY_ACCESS_TOKEN or "
    "CHRONOS_TEST_SECONDARY_EMAIL/CHRONOS_TEST_SECONDARY_PASSWORD. "
    "Set CHRONOS_ALLOW_EPHEMERAL_SECONDARY=1 to opt into temporary service-role provisioning."
)


def _fake_auth_headers(
    user_id: str,
    *,
    role: str = "member",
    tier: str = "hobbyist",
    org_id: str = "org-default",
) -> dict[str, str]:
    return {
        "Authorization": f"Bearer test-token-for-{user_id}",
        "X-Chronos-Role": role,
        "X-Chronos-Tier": tier,
        "X-Chronos-Org": org_id,
    }


def _uses_fake_auth_headers(*headers: dict[str, str] | None) -> bool:
    for header_set in headers:
        if not header_set:
            continue
        if header_set.get("Authorization", "").startswith("Bearer test-token-for-"):
            return True
    return False


def _enable_test_auth_override() -> None:
    os.environ.setdefault("TEST_AUTH_OVERRIDE", "1")
    if api_dependencies.settings.test_auth_override:
        return
    overridden_settings = replace(app_config.settings, test_auth_override=True)
    app_config.settings = overridden_settings
    api_dependencies.settings = overridden_settings


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _write_json(output_path: str | os.PathLike[str] | None, payload: dict[str, Any]) -> None:
    if not output_path:
        return
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def _default_live_smoke_output_path(backend_name: str) -> Path:
    _EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    return _EVIDENCE_DIR / f"{backend_name}-live-smoke.json"


def default_staging_latency_output_path() -> Path:
    _EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    return _EVIDENCE_DIR / "staging-latency.json"


def _response_body(response: httpx.Response | Any) -> str:
    try:
        return json.dumps(response.json())
    except Exception:
        return getattr(response, "text", "<no body>")


def _extract_access_token(auth_response: Any) -> str:
    session = getattr(auth_response, "session", None)
    if session is None and isinstance(auth_response, dict):
        session = auth_response.get("session")
    if isinstance(session, dict):
        token = session.get("access_token") or session.get("accessToken")
    else:
        token = getattr(session, "access_token", None)
    if not token:
        raise LiveSmokePrerequisiteError("Unable to resolve an access token from the Supabase auth response.")
    return str(token)


def _resolve_real_auth_headers(prefix: str) -> dict[str, str]:
    access_token = os.getenv(f"{prefix}_ACCESS_TOKEN", "").strip()
    if not access_token:
        email = os.getenv(f"{prefix}_EMAIL", "").strip()
        password = os.getenv(f"{prefix}_PASSWORD", "").strip()
        if not email or not password:
            raise LiveSmokePrerequisiteError(
                f"{prefix}_ACCESS_TOKEN or {prefix}_EMAIL/{prefix}_PASSWORD are required for the real Supabase-backed smoke."
            )
        access_token = _extract_access_token(SupabaseAuthService().sign_in_with_password(email=email, password=password))

    headers = {"Authorization": f"Bearer {access_token}"}
    test_auth_override_enabled = (
        os.getenv("TEST_AUTH_OVERRIDE", "").strip() == "1"
        or app_config.settings.test_auth_override
        or api_dependencies.settings.test_auth_override
    )
    override_envs = {
        "ROLE": "X-Chronos-Role",
        "TIER": "X-Chronos-Tier",
        "ORG": "X-Chronos-Org",
    }
    ineffective_overrides = [
        f"{prefix}_{suffix}"
        for suffix in override_envs
        if os.getenv(f"{prefix}_{suffix}", "").strip()
    ]
    if ineffective_overrides and not test_auth_override_enabled:
        configured = ", ".join(ineffective_overrides)
        raise LiveSmokePrerequisiteError(
            f"{configured} are ineffective in real-auth mode unless TEST_AUTH_OVERRIDE=1. "
            "Remove those env vars or enable test auth override."
        )
    for suffix, header_name in override_envs.items():
        value = os.getenv(f"{prefix}_{suffix}", "").strip()
        if value:
            headers[header_name] = value
    return headers


def resolve_primary_actor_headers(*, require_real_auth: bool) -> dict[str, str]:
    if require_real_auth:
        return _resolve_real_auth_headers("CHRONOS_TEST")
    return _fake_auth_headers("live-upload-user")


def resolve_secondary_actor_headers(*, require_real_auth: bool) -> dict[str, str]:
    if require_real_auth:
        return _resolve_real_auth_headers("CHRONOS_TEST_SECONDARY")
    return _fake_auth_headers("live-upload-intruder")


def _provision_ephemeral_secondary_headers() -> tuple[dict[str, str], str]:
    client = SupabaseClient()
    try:
        admin = client.service_role_sdk_client().auth.admin
    except Exception as exc:  # pragma: no cover - exercised only in live integration mode
        raise LiveSmokePrerequisiteError(
            "Supabase service-role configuration is required to provision an ephemeral secondary live-smoke user."
        ) from exc

    email = f"packet4a-secondary-{uuid4().hex[:12]}@example.com"
    password = f"Packet4A-{uuid4().hex}!"
    user_id: str | None = None
    try:
        created = admin.create_user(
            {
                "email": email,
                "password": password,
                "email_confirm": True,
            }
        )
        user = getattr(created, "user", None)
        user_id = getattr(user, "id", None)
        if not user_id:
            raise LiveSmokePrerequisiteError("Supabase admin user creation did not return a user id.")
        token = _extract_access_token(SupabaseAuthService().sign_in_with_password(email=email, password=password))
        return {"Authorization": f"Bearer {token}"}, str(user_id)
    except Exception as exc:  # pragma: no cover - exercised only in live integration mode
        if user_id is not None:
            _delete_ephemeral_secondary_user(str(user_id))
        raise LiveSmokePrerequisiteError("Failed to provision an ephemeral secondary Supabase user for Packet 4A.") from exc


def _delete_ephemeral_secondary_user(user_id: str) -> None:
    try:  # pragma: no cover - exercised only in live integration mode
        SupabaseClient().service_role_sdk_client().auth.admin.delete_user(user_id)
    except Exception:
        return


def _require_current_actor(client: TestClient, headers: dict[str, str]) -> ActorContext:
    response = client.get("/v1/users/me", headers=headers)
    if response.status_code != 200:
        raise LiveSmokeExecutionError(f"/v1/users/me returned {response.status_code}: {_response_body(response)}")
    payload = response.json()
    return ActorContext(headers=headers, user_id=payload["user_id"], org_id=payload["org_id"])


def _supabase_snapshot(upload_id: str) -> dict[str, Any]:
    client = SupabaseClient()
    with psycopg.connect(client.direct_db_dsn(), row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            """
            select external_upload_id, external_user_id, status, object_path, media_uri, resumable_session_url,
                   created_at, updated_at, completed_at
            from public.upload_sessions
            where external_upload_id = %s
            limit 1
            """,
            (upload_id,),
        )
        session = cur.fetchone()
        cur.execute(
            """
            select external_upload_id, external_user_id, object_path, checksum_sha256, mime_type, size_bytes, created_at
            from public.gcs_object_pointers
            where external_upload_id = %s
            limit 1
            """,
            (upload_id,),
        )
        pointer = cur.fetchone()
    return {
        "backend": "supabase",
        "session": _json_safe(dict(session)) if session else None,
        "pointer": _json_safe(dict(pointer)) if pointer else None,
    }


def _memory_snapshot(upload_id: str) -> dict[str, Any]:
    session = _STORE.upload_sessions.get(upload_id)
    pointer = _STORE.gcs_object_pointers.get(upload_id)
    return {
        "backend": "memory",
        "session": _json_safe(dict(session)) if session else None,
        "pointer": _json_safe(dict(pointer)) if pointer else None,
    }


def snapshot_upload_artifacts(upload_id: str) -> dict[str, Any]:
    return _supabase_snapshot(upload_id) if phase2_backend_name() == "supabase" else _memory_snapshot(upload_id)


def _valid_upload_request(size_bytes: int) -> dict[str, Any]:
    return {
        "original_filename": "packet4a-live.mov",
        "mime_type": "video/quicktime",
        "size_bytes": size_bytes,
    }


def _expect_status(response: Any, expected_status: int, label: str) -> None:
    if response.status_code != expected_status:
        raise LiveSmokeExecutionError(f"{label} returned {response.status_code}: {_response_body(response)}")


def run_packet4a_live_smoke(
    *,
    client: TestClient,
    primary_headers: dict[str, str],
    secondary_headers: dict[str, str] | None,
    output_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    if _uses_fake_auth_headers(primary_headers, secondary_headers):
        _enable_test_auth_override()
    backend_name = phase2_backend_name()
    resolved_output_path = Path(output_path) if output_path else _default_live_smoke_output_path(backend_name)
    ephemeral_secondary_user_id: str | None = None
    if secondary_headers is None and backend_name == "supabase":
        if os.getenv("CHRONOS_ALLOW_EPHEMERAL_SECONDARY", "").strip() == "1":
            secondary_headers, ephemeral_secondary_user_id = _provision_ephemeral_secondary_headers()
        else:
            raise LiveSmokePrerequisiteError(_SECONDARY_PREREQ_MESSAGE)

    primary_actor = _require_current_actor(client, primary_headers)
    upload_size = _LIVE_UPLOAD_SIZE_BYTES
    first_chunk_end = _LIVE_CHUNK_SIZE_BYTES - 1
    second_chunk_size = upload_size - _LIVE_CHUNK_SIZE_BYTES
    try:
        create_response = client.post(
            "/v1/upload",
            headers=primary_actor.headers,
            json=_valid_upload_request(upload_size),
        )
        _expect_status(create_response, 200, "create upload")
        created = create_response.json()
        after_create = snapshot_upload_artifacts(created["upload_id"])

        secondary_resume_status = None
        secondary_finalize_status = None
        if secondary_headers is not None:
            secondary_resume = client.post(
                f"/v1/upload/{created['upload_id']}/resume",
                headers=secondary_headers,
            )
            secondary_finalize = client.patch(
                f"/v1/upload/{created['upload_id']}",
                headers=secondary_headers,
                json={"size_bytes": upload_size},
            )
            secondary_resume_status = secondary_resume.status_code
            secondary_finalize_status = secondary_finalize.status_code
            if secondary_resume_status != 404:
                raise LiveSmokeExecutionError(
                    f"secondary resume should return 404, got {secondary_resume_status}: {_response_body(secondary_resume)}"
                )
            if secondary_finalize_status != 404:
                raise LiveSmokeExecutionError(
                    f"secondary finalize should return 404, got {secondary_finalize_status}: {_response_body(secondary_finalize)}"
                )

        first_chunk = httpx.put(
            created["resumable_session_url"],
            headers={
                "Content-Length": str(_LIVE_CHUNK_SIZE_BYTES),
                "Content-Range": f"bytes 0-{first_chunk_end}/{upload_size}",
                "Content-Type": "video/quicktime",
            },
            content=b"0" * _LIVE_CHUNK_SIZE_BYTES,
            timeout=20.0,
        )
        if first_chunk.status_code != 308:
            raise LiveSmokeExecutionError(f"first chunk upload returned {first_chunk.status_code}: {_response_body(first_chunk)}")

        resume_response = client.post(
            f"/v1/upload/{created['upload_id']}/resume",
            headers=primary_actor.headers,
        )
        _expect_status(resume_response, 200, "resume upload")
        resumed = resume_response.json()
        after_resume = snapshot_upload_artifacts(created["upload_id"])

        second_chunk = httpx.put(
            resumed["resumable_session_url"],
            headers={
                "Content-Length": str(second_chunk_size),
                "Content-Range": f"bytes {_LIVE_CHUNK_SIZE_BYTES}-{upload_size - 1}/{upload_size}",
                "Content-Type": "video/quicktime",
            },
            content=b"1" * second_chunk_size,
            timeout=20.0,
        )
        if second_chunk.status_code not in {200, 201}:
            raise LiveSmokeExecutionError(f"second chunk upload returned {second_chunk.status_code}: {_response_body(second_chunk)}")

        finalize_response = client.patch(
            f"/v1/upload/{created['upload_id']}",
            headers=primary_actor.headers,
            json={"size_bytes": upload_size},
        )
        _expect_status(finalize_response, 200, "finalize upload")
        finalized = finalize_response.json()
        after_finalize = snapshot_upload_artifacts(created["upload_id"])

        result = {
            "backend": backend_name,
            "creator_user_id": primary_actor.user_id,
            "upload_id": created["upload_id"],
            "object_path": created["object_path"],
            "same_upload_id": resumed["upload_id"] == created["upload_id"] == finalized["upload_id"],
            "same_object_path": resumed["object_path"] == created["object_path"] == finalized["object_path"],
            "first_chunk_status": first_chunk.status_code,
            "resume_offset": resumed["next_byte_offset"],
            "resume_upload_complete": resumed["upload_complete"],
            "session_regenerated": resumed["session_regenerated"],
            "second_chunk_status": second_chunk.status_code,
            "final_status": finalized["status"],
            "secondary_resume_status": secondary_resume_status,
            "secondary_finalize_status": secondary_finalize_status,
            "after_create_status": after_create["session"]["status"] if after_create["session"] else None,
            "after_resume_status": after_resume["session"]["status"] if after_resume["session"] else None,
            "after_finalize_status": after_finalize["session"]["status"] if after_finalize["session"] else None,
            "pointer_persisted": bool(after_finalize["pointer"]),
            "resume_session_url_persisted": (
                after_resume["session"]["resumable_session_url"] == resumed["resumable_session_url"]
                if after_resume["session"]
                else False
            ),
            "pointer_object_path": after_finalize["pointer"]["object_path"] if after_finalize["pointer"] else None,
            "pointer_owner_matches_creator": (
                after_finalize["pointer"]["external_user_id"] == primary_actor.user_id
                if after_finalize["pointer"] and after_finalize["pointer"].get("external_user_id")
                else after_finalize["backend"] == "memory"
            ),
            "session_snapshots": {
                "after_create": after_create["session"],
                "after_resume": after_resume["session"],
                "after_finalize": after_finalize["session"],
            },
            "pointer_snapshots": {
                "after_create": after_create["pointer"],
                "after_resume": after_resume["pointer"],
                "after_finalize": after_finalize["pointer"],
            },
        }
        _write_json(resolved_output_path, result)
        return result
    finally:
        if ephemeral_secondary_user_id is not None:
            _delete_ephemeral_secondary_user(ephemeral_secondary_user_id)


def _percentile(samples: list[float], ratio: float) -> float:
    ordered = sorted(samples)
    index = min(max(math.ceil(len(ordered) * ratio) - 1, 0), len(ordered) - 1)
    return ordered[index]


async def measure_packet4a_staging_latency(
    *,
    base_url: str,
    headers: dict[str, str],
    total_requests: int,
    concurrency: int,
) -> dict[str, Any]:
    if total_requests <= 0:
        raise LiveSmokePrerequisiteError("total_requests must be greater than 0.")
    if concurrency <= 0:
        raise LiveSmokePrerequisiteError("concurrency must be greater than 0.")
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=30.0) as http:
        async def send_request(index: int) -> float:
            async with semaphore:
                started = perf_counter()
                response = await http.post(
                    "/v1/upload",
                    headers=headers,
                    json={
                        "original_filename": f"packet4a-latency-{index}.mov",
                        "mime_type": "video/quicktime",
                        "size_bytes": 10,
                    },
                )
                elapsed = perf_counter() - started
                if response.status_code != 200:
                    raise LiveSmokeExecutionError(
                        f"staging upload create {index} returned {response.status_code}: {_response_body(response)}"
                    )
                return elapsed

        samples = list(await asyncio.gather(*(send_request(index) for index in range(total_requests))))

    return {
        "base_url": base_url.rstrip("/"),
        "total_requests": total_requests,
        "concurrency": concurrency,
        "p50_seconds": round(_percentile(samples, 0.50), 4),
        "p95_seconds": round(_percentile(samples, 0.95), 4),
        "p99_seconds": round(_percentile(samples, 0.99), 4),
    }


def _run_cli() -> None:
    parser = argparse.ArgumentParser(description="Packet 4A live smoke and staging latency probe.")
    parser.add_argument(
        "--mode",
        choices=("live-smoke", "staging-latency"),
        default="live-smoke",
    )
    parser.add_argument("--output", default="", help="Optional JSON file for evidence output.")
    parser.add_argument(
        "--require-real-auth",
        action="store_true",
        help="Use real Supabase auth credentials instead of local test-auth override headers.",
    )
    parser.add_argument(
        "--require-secondary-auth",
        action="store_true",
        help="Require a second actor for owner-boundary validation.",
    )
    args = parser.parse_args()

    try:
        if args.mode == "live-smoke":
            primary_headers = resolve_primary_actor_headers(require_real_auth=args.require_real_auth)
            secondary_headers = None
            if args.require_secondary_auth:
                secondary_headers = resolve_secondary_actor_headers(require_real_auth=args.require_real_auth)
            if _uses_fake_auth_headers(primary_headers, secondary_headers):
                _enable_test_auth_override()
            result = run_packet4a_live_smoke(
                client=TestClient(app),
                primary_headers=primary_headers,
                secondary_headers=secondary_headers,
                output_path=args.output or None,
            )
        else:
            base_url = os.getenv("CHRONOS_PACKET4A_STAGING_BASE_URL", "").strip()
            if not base_url:
                raise LiveSmokePrerequisiteError("CHRONOS_PACKET4A_STAGING_BASE_URL is required for staging latency mode.")
            headers = _resolve_real_auth_headers("CHRONOS_PACKET4A_STAGING")
            total_requests = int(os.getenv("CHRONOS_PACKET4A_STAGING_LATENCY_TOTAL", "20"))
            concurrency = int(os.getenv("CHRONOS_PACKET4A_STAGING_LATENCY_CONCURRENCY", "5"))
            result = asyncio.run(
                measure_packet4a_staging_latency(
                    base_url=base_url,
                    headers=headers,
                    total_requests=total_requests,
                    concurrency=concurrency,
                )
            )
            _write_json(args.output or default_staging_latency_output_path(), result)
        print(json.dumps(_json_safe(result), indent=2))
    except (LiveSmokePrerequisiteError, LiveSmokeExecutionError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    _run_cli()
