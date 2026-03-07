#!/usr/bin/env python3
"""Maps to: OPS-001"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any


REQUIRED_SECRET_REFS = {
    "SUPABASE_URL": "SUPABASE_URL_DEV",
    "SUPABASE_ANON_KEY": "SUPABASE_ANON_KEY_DEV",
    "SUPABASE_SERVICE_ROLE_KEY": "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_DB_HOST": "SUPABASE_DB_HOST",
    "SUPABASE_DB_PORT": "SUPABASE_DB_PORT",
    "SUPABASE_DB_NAME": "SUPABASE_DB_NAME",
    "SUPABASE_DB_USER": "SUPABASE_DB_USER",
    "SUPABASE_DB_PASSWORD": "SUPABASE_DB_PASSWORD",
    "JOB_WORKER_TRUSTED_TOKEN": "JOB_WORKER_TRUSTED_TOKEN",
}

REQUIRED_PLAIN_ENVS = {
    "ENVIRONMENT": "staging",
    "SEGMENT_CACHE_MODE": "redis",
    "JOB_DISPATCH_MODE": "pubsub",
    "JOB_PROGRESS_MODE": "supabase",
}

REQUIRED_NONEMPTY_ENVS = {
    "BUILD_SHA",
    "BUILD_TIME",
    "REDIS_URL",
}

FORBIDDEN_LITERAL_VALUES = {
    "SUPABASE_SERVICE_ROLE_KEY": {"test_service_role", "", None},
    "JOB_WORKER_TRUSTED_TOKEN": {"", None},
    "SUPABASE_DB_PASSWORD": {"", None},
    "BUILD_SHA": {"local", "", None},
    "BUILD_TIME": {"unknown", "", None},
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Cloud Run runtime secret/env hardening.")
    parser.add_argument("--service", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--project", required=True)
    return parser.parse_args()


def _describe_service(*, service: str, region: str, project: str) -> dict[str, Any]:
    output = subprocess.check_output(
        [
            "gcloud",
            "run",
            "services",
            "describe",
            service,
            "--project",
            project,
            "--region",
            region,
            "--format=json",
        ],
        text=True,
    )
    return json.loads(output)


def _env_map(service: dict[str, Any]) -> dict[str, dict[str, Any]]:
    containers = service["spec"]["template"]["spec"]["containers"]
    env_entries = containers[0].get("env", [])
    return {entry["name"]: entry for entry in env_entries}


def _check_secret_refs(env_map: dict[str, dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for env_name, secret_name in REQUIRED_SECRET_REFS.items():
        entry = env_map.get(env_name)
        if entry is None:
            failures.append(f"Missing runtime setting: {env_name}")
            continue
        secret_ref = ((entry.get("valueFrom") or {}).get("secretKeyRef")) or {}
        if secret_ref.get("name") != secret_name:
            failures.append(f"{env_name} must reference Secret Manager secret {secret_name}")
    return failures


def _check_plain_envs(env_map: dict[str, dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for env_name, expected_value in REQUIRED_PLAIN_ENVS.items():
        entry = env_map.get(env_name)
        if entry is None:
            failures.append(f"Missing runtime setting: {env_name}")
            continue
        if entry.get("value") != expected_value:
            failures.append(f"{env_name} must equal {expected_value}")
    return failures


def _check_forbidden_literals(env_map: dict[str, dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for env_name, forbidden_values in FORBIDDEN_LITERAL_VALUES.items():
        entry = env_map.get(env_name)
        if entry is None:
            continue
        if "value" in entry and entry.get("value") in forbidden_values:
            failures.append(f"{env_name} is using a forbidden literal value")
    return failures


def _check_required_nonempty_envs(env_map: dict[str, dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for env_name in REQUIRED_NONEMPTY_ENVS:
        entry = env_map.get(env_name)
        if entry is None:
            failures.append(f"Missing runtime setting: {env_name}")
            continue
        value = entry.get("value")
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{env_name} must be a non-empty literal env value")
    return failures


def _check_env_formats(env_map: dict[str, dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    build_sha = (env_map.get("BUILD_SHA") or {}).get("value", "")
    if isinstance(build_sha, str):
        normalized = build_sha.removesuffix("-dirty")
        if len(normalized) < 7 or any(ch not in "0123456789abcdef" for ch in normalized.lower()):
            failures.append("BUILD_SHA must look like a git commit SHA")
    redis_url = (env_map.get("REDIS_URL") or {}).get("value", "")
    if isinstance(redis_url, str) and not redis_url.startswith("redis://"):
        failures.append("REDIS_URL must use the redis:// scheme")
    return failures


def main() -> int:
    args = _parse_args()
    service = _describe_service(service=args.service, region=args.region, project=args.project)
    env_map = _env_map(service)

    failures = []
    failures.extend(_check_secret_refs(env_map))
    failures.extend(_check_plain_envs(env_map))
    failures.extend(_check_required_nonempty_envs(env_map))
    failures.extend(_check_forbidden_literals(env_map))
    failures.extend(_check_env_formats(env_map))

    revision = service["status"].get("latestReadyRevisionName", "unknown")
    if failures:
        print(f"FAIL: runtime verification failed for {args.service} @ {revision}")
        for item in failures:
            print(f"- {item}")
        return 1

    print(f"PASS: runtime verification passed for {args.service} @ {revision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
