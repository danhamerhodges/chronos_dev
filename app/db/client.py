"""Supabase client wrapper for ENG-016 baseline."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote_plus
from uuid import uuid5, NAMESPACE_URL

import httpx
import psycopg
from supabase import Client, create_client

from app.config import settings


class SupabaseClient:
    def __init__(self, base_url: str | None = None, anon_key: str | None = None) -> None:
        resolved_base_url = settings.supabase_url if base_url is None else base_url
        resolved_anon_key = settings.supabase_anon_key if anon_key is None else anon_key

        self.base_url = resolved_base_url.rstrip("/") if resolved_base_url else ""
        self.anon_key = resolved_anon_key or ""

    def is_configured(self) -> bool:
        return bool(self.base_url and self.anon_key)

    def sdk_client(self) -> Client:
        if not self.is_configured():
            raise ValueError("Supabase configuration is required")
        return create_client(self.base_url, self.anon_key)

    def service_role_sdk_client(self) -> Client:
        if not self.base_url or not settings.supabase_service_role_key:
            raise ValueError("Supabase service role configuration is required")
        return create_client(self.base_url, settings.supabase_service_role_key)

    def user_scoped_headers(self, access_token: str) -> dict[str, str]:
        if not self.is_configured():
            raise ValueError("Supabase configuration is required")
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def service_role_headers(self) -> dict[str, str]:
        if not self.base_url or not settings.supabase_service_role_key:
            raise ValueError("Supabase service role configuration is required")
        return {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def direct_db_dsn(self) -> str:
        if settings.supabase_db_url:
            return settings.supabase_db_url
        required = (
            settings.supabase_db_host,
            settings.supabase_db_port,
            settings.supabase_db_name,
            settings.supabase_db_user,
            settings.supabase_db_password,
        )
        if not all(required):
            raise ValueError("Supabase direct database configuration is required")
        password = quote_plus(settings.supabase_db_password)
        return (
            f"postgresql://{settings.supabase_db_user}:{password}"
            f"@{settings.supabase_db_host}:{settings.supabase_db_port}/{settings.supabase_db_name}"
            "?sslmode=require"
        )

    def rest_url(self, table_name: str) -> str:
        if not self.base_url:
            raise ValueError("Supabase configuration is required")
        return f"{self.base_url}/rest/v1/{table_name}"

    def _require_rest_headers(self, headers: dict[str, str] | None) -> dict[str, str]:
        if headers is None:
            raise ValueError(
                "Explicit REST headers are required. Use user_scoped_headers() or an explicit *_service_role method."
            )
        return headers

    def rest_select(self, table_name: str, *, params: dict[str, str], headers: dict[str, str] | None = None) -> list[dict[str, Any]]:
        request_headers = self._require_rest_headers(headers)
        with httpx.Client(timeout=10.0) as client:
            response = client.get(self.rest_url(table_name), headers=request_headers, params=params)
            response.raise_for_status()
            return response.json()

    def rest_insert(
        self,
        table_name: str,
        *,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        request_headers = self._require_rest_headers(headers)
        with httpx.Client(timeout=10.0) as client:
            response = client.post(self.rest_url(table_name), headers=request_headers, json=payload)
            response.raise_for_status()
            return response.json()

    def rest_upsert(
        self,
        table_name: str,
        *,
        payload: dict[str, Any],
        on_conflict: str,
        headers: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        request_headers = dict(self._require_rest_headers(headers))
        request_headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                self.rest_url(table_name),
                headers=request_headers,
                params={"on_conflict": on_conflict},
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def rest_update(
        self,
        table_name: str,
        *,
        payload: dict[str, Any],
        params: dict[str, str],
        headers: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        request_headers = self._require_rest_headers(headers)
        with httpx.Client(timeout=10.0) as client:
            response = client.patch(
                self.rest_url(table_name),
                headers=request_headers,
                params=params,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def rest_delete(
        self,
        table_name: str,
        *,
        params: dict[str, str],
        headers: dict[str, str] | None = None,
    ) -> None:
        request_headers = dict(self._require_rest_headers(headers))
        request_headers["Prefer"] = "return=minimal"
        with httpx.Client(timeout=10.0) as client:
            response = client.delete(
                self.rest_url(table_name),
                headers=request_headers,
                params=params,
            )
            response.raise_for_status()

    def rest_select_service_role(self, table_name: str, *, params: dict[str, str]) -> list[dict[str, Any]]:
        return self.rest_select(table_name, params=params, headers=self.service_role_headers())

    def rest_insert_service_role(self, table_name: str, *, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return self.rest_insert(table_name, payload=payload, headers=self.service_role_headers())

    def rest_upsert_service_role(
        self,
        table_name: str,
        *,
        payload: dict[str, Any],
        on_conflict: str,
    ) -> list[dict[str, Any]]:
        return self.rest_upsert(
            table_name,
            payload=payload,
            on_conflict=on_conflict,
            headers=self.service_role_headers(),
        )

    def rest_update_service_role(
        self,
        table_name: str,
        *,
        payload: dict[str, Any],
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        return self.rest_update(
            table_name,
            payload=payload,
            params=params,
            headers=self.service_role_headers(),
        )

    def rest_delete_service_role(self, table_name: str, *, params: dict[str, str]) -> None:
        self.rest_delete(table_name, params=params, headers=self.service_role_headers())

    def auth_user(self, access_token: str) -> dict[str, Any]:
        if not self.is_configured():
            raise ValueError("Supabase configuration is required")
        headers = self.user_scoped_headers(access_token)
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{self.base_url}/auth/v1/user", headers=headers)
            response.raise_for_status()
            return response.json()

    def healthcheck(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "supabase not configured"
        # A lightweight endpoint probe. Keep timeout short for tests.
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{self.base_url}/rest/v1/", headers={"apikey": self.anon_key})
            return resp.status_code < 500, f"status={resp.status_code}"

    def pooling_profile(self) -> dict[str, str]:
        return {
            "pooler": "supabase-supavisor",
            "mode": "transaction",
            "tls_required": "true",
        }

    def backup_restore_profile(self) -> dict[str, str]:
        return {
            "backups": "managed-daily-snapshots",
            "restore": "point-in-time-recovery-supported",
        }

    def broadcast_realtime_service_role(self, *, topic: str, event: str, payload: dict[str, Any]) -> None:
        with psycopg.connect(self.direct_db_dsn()) as conn, conn.cursor() as cur:
            cur.execute(
                "select realtime.send(%s::jsonb, %s, %s, %s)",
                (json.dumps(payload, default=str), event, topic, True),
            )

    def query_table(self, table_name: str, columns: str = "*", limit: int = 1) -> list[dict[str, Any]]:
        """Execute a bounded table query using the Supabase SDK."""
        result = self.sdk_client().table(table_name).select(columns).limit(limit).execute()
        data = getattr(result, "data", None) or []
        return data

    def synthetic_user_id(self, access_token: str) -> str:
        return str(uuid5(NAMESPACE_URL, access_token))
