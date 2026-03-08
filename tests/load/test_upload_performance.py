"""
Maps to:
- FR-001
- AC-FR-001-02
"""

from __future__ import annotations

import asyncio
from time import perf_counter

import httpx

from app.main import app
from tests.helpers.auth import fake_auth_header


class FastSessionClient:
    def create_resumable_session(self, *, bucket_name: str, object_path: str, mime_type: str, size_bytes: int) -> str:
        del bucket_name, object_path, mime_type, size_bytes
        return "https://storage.googleapis.com/upload/resumable/fake/perf"

    def probe_resumable_session(self, *, session_url: str, size_bytes: int):  # pragma: no cover - not used in this test
        del session_url, size_bytes
        raise AssertionError("probe_resumable_session should not be used in upload session creation load testing")

    def fetch_object_metadata(self, *, bucket_name: str, object_path: str) -> dict[str, object] | None:
        del bucket_name, object_path
        return {"size_bytes": 1024 * 1024, "mime_type": "video/quicktime"}


def _percentile(samples: list[float], ratio: float) -> float:
    ordered = sorted(samples)
    index = max(int(len(ordered) * ratio) - 1, 0)
    return ordered[index]


async def _run_concurrent_upload_creation() -> list[float]:
    transport = httpx.ASGITransport(app=app)
    semaphore = asyncio.Semaphore(100)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        async def send_request(request_index: int) -> float:
            async with semaphore:
                started = perf_counter()
                response = await async_client.post(
                    "/v1/upload",
                    headers=fake_auth_header(f"perf-user-{request_index}"),
                    json={
                        "original_filename": f"perf-{request_index}.mov",
                        "mime_type": "video/quicktime",
                        "size_bytes": 1024 * 1024,
                        "checksum_sha256": "abc12345def67890",
                    },
                )
                elapsed = perf_counter() - started
                assert response.status_code == 200
                return elapsed

        return list(await asyncio.gather(*(send_request(index) for index in range(1000))))


def test_upload_session_creation_meets_latency_targets_under_concurrent_load(monkeypatch) -> None:
    import app.services.rate_limits as rate_limits
    from app.api import uploads

    monkeypatch.setattr(uploads._upload_service, "_session_client", FastSessionClient())
    monkeypatch.setattr(rate_limits, "_limit_for_tier", lambda plan_tier: 10000)
    samples = asyncio.run(_run_concurrent_upload_creation())

    p50 = _percentile(samples, 0.50)
    p95 = _percentile(samples, 0.95)
    p99 = _percentile(samples, 0.99)

    assert len(samples) == 1000
    assert p50 < 0.5
    assert p95 < 1.2
    assert p99 < 2.0
