"""Supabase client wrapper for ENG-016 baseline."""

from __future__ import annotations

from typing import Any

import httpx
from supabase import Client, create_client

from app.config import settings


class SupabaseClient:
    def __init__(self, base_url: str | None = None, anon_key: str | None = None) -> None:
        self.base_url = (base_url or settings.supabase_url).rstrip("/")
        self.anon_key = anon_key or settings.supabase_anon_key

    def is_configured(self) -> bool:
        return bool(self.base_url and self.anon_key)

    def sdk_client(self) -> Client:
        if not self.is_configured():
            raise ValueError("Supabase configuration is required")
        return create_client(self.base_url, self.anon_key)

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

    def query_table(self, table_name: str, columns: str = "*", limit: int = 1) -> list[dict[str, Any]]:
        """Execute a bounded table query using the Supabase SDK."""
        result = self.sdk_client().table(table_name).select(columns).limit(limit).execute()
        data = getattr(result, "data", None) or []
        return data
