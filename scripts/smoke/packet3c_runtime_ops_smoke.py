#!/usr/bin/env python3
"""Opt-in live smoke for Packet 3C runtime ops surfaces."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.smoke.async_jobs_runtime_smoke import _build_auth_headers, _poll_job_status, _pull_matching_message, _require_env, _valid_job_request


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    return value.lower() not in {"0", "false", "no"}


async def _run_async_job(
    http: httpx.AsyncClient,
    *,
    base_url: str,
    auth_headers: dict[str, str],
    trusted_token: str,
    job_request: dict[str, Any],
) -> dict[str, Any]:
    created_response = await http.post(f"{base_url}/v1/jobs", headers=auth_headers, json=job_request)
    created_response.raise_for_status()
    created = created_response.json()
    job_id = created["job_id"]

    subscriber, received, _dispatch = _pull_matching_message(job_id)
    worker_payload = {
        "message": {
            "data": __import__("base64").b64encode(received.message.data).decode("utf-8"),
            "attributes": dict(received.message.attributes),
        }
    }
    try:
        worker_response = await http.post(
            f"{base_url}/internal/workers/jobs/run",
            headers={"X-Chronos-Worker-Token": trusted_token},
            json=worker_payload,
            timeout=httpx.Timeout(180.0, connect=20.0),
        )
        worker_response.raise_for_status()
    finally:
        subscriber.acknowledge(
            request={"subscription": _require_env("CHRONOS_ASYNC_SMOKE_PUBSUB_SUBSCRIPTION"), "ack_ids": [received.ack_id]}
        )
    final_status = await _poll_job_status(http, base_url=base_url, headers=auth_headers, job_id=job_id)
    return final_status


async def _run() -> None:
    if os.getenv("CHRONOS_RUN_PACKET3C_RUNTIME_SMOKE") != "1":
        raise SystemExit("Set CHRONOS_RUN_PACKET3C_RUNTIME_SMOKE=1 to run the Packet 3C runtime ops smoke.")

    base_url = _require_env("CHRONOS_ASYNC_SMOKE_BASE_URL").rstrip("/")
    auth_headers = _build_auth_headers()
    trusted_token = _require_env("JOB_WORKER_TRUSTED_TOKEN")
    require_degraded = _env_bool("CHRONOS_PACKET3C_EXPECT_CACHE_DEGRADED", True)
    allow_runtime_snapshot_forbidden = _env_bool("CHRONOS_PACKET3C_ALLOW_RUNTIME_SNAPSHOT_FORBIDDEN", True)
    shared_checksum = os.getenv("CHRONOS_PACKET3C_SOURCE_CHECKSUM", f"packet3c-cache-smoke-{uuid4().hex}")
    first_request = _valid_job_request()
    first_request["source_asset_checksum"] = shared_checksum
    second_request = dict(first_request)

    async with httpx.AsyncClient(timeout=20.0) as http:
        first_job = await _run_async_job(
            http,
            base_url=base_url,
            auth_headers=auth_headers,
            trusted_token=trusted_token,
            job_request=first_request,
        )
        second_job = await _run_async_job(
            http,
            base_url=base_url,
            auth_headers=auth_headers,
            trusted_token=trusted_token,
            job_request=second_request,
        )

        degraded_alert_response = await http.post(
            f"{base_url}/internal/ops/alerts/evaluate",
            headers={"X-Chronos-Worker-Token": trusted_token},
            json={"cache_summary": {"degraded": True, "path": "packet3c-smoke"}},
        )
        degraded_alert_response.raise_for_status()
        degraded_alert = degraded_alert_response.json()

        runtime_snapshot: dict[str, Any] | None = None
        runtime_response = await http.get(f"{base_url}/v1/ops/runtime", headers=auth_headers)
        if runtime_response.status_code == 200:
            runtime_snapshot = runtime_response.json()
        elif not allow_runtime_snapshot_forbidden:
            runtime_response.raise_for_status()

        metrics_response = await http.get(f"{base_url}/v1/metrics")
        metrics_response.raise_for_status()
        metrics_payload = metrics_response.text

    first_cache = first_job.get("cache_summary") or {}
    second_cache = second_job.get("cache_summary") or {}
    if require_degraded and not (first_cache.get("degraded") or second_cache.get("degraded")):
        raise SystemExit("Packet 3C smoke expected degraded cache mode, but no degraded cache summary was observed.")
    if not require_degraded and second_cache.get("hits", 0) <= 0:
        raise SystemExit("Packet 3C smoke expected a real Redis cache hit on the second job, but no cache hits were observed.")

    if "runtime_gauge" not in metrics_payload or "incident_total" not in metrics_payload:
        raise SystemExit("Packet 3C metrics payload is missing runtime gauge or incident metrics.")
    if "alert_delivery_total" not in metrics_payload:
        raise SystemExit("Packet 3C metrics payload is missing alert delivery counters.")
    if runtime_snapshot is not None and not runtime_snapshot.get("alerts"):
        raise SystemExit("Packet 3C runtime snapshot did not record any alert deliveries.")

    print(
        {
            "first_job_id": first_job["job_id"],
            "second_job_id": second_job["job_id"],
            "first_status": first_job["status"],
            "second_status": second_job["status"],
            "first_cache_summary": first_cache,
            "second_cache_summary": second_cache,
            "runtime_snapshot_status": "available" if runtime_snapshot is not None else "forbidden",
            "runtime_snapshot_incidents": len(runtime_snapshot.get("incidents", [])) if runtime_snapshot is not None else None,
            "runtime_snapshot_alert_routes": runtime_snapshot.get("alert_routes", {}) if runtime_snapshot is not None else {},
            "runtime_snapshot_alerts": len(runtime_snapshot.get("alerts", [])) if runtime_snapshot is not None else None,
            "alert_evaluation_incidents": degraded_alert.get("incident_count"),
            "metrics_runtime_gauge": "runtime_gauge" in metrics_payload,
            "metrics_incident_total": "incident_total" in metrics_payload,
            "metrics_alert_delivery_total": "alert_delivery_total" in metrics_payload,
        }
    )


if __name__ == "__main__":
    asyncio.run(_run())
