"""
Maps to:
- ENG-014
"""

from __future__ import annotations

import asyncio
from time import perf_counter

import httpx
import pytest

from app.main import app
from app.db.phase2_store import reset_phase2_store
from tests.helpers.auth import fake_auth_header
from tests.helpers.previews import save_configuration, seed_completed_upload, seed_detection


def _percentile(samples: list[float], ratio: float) -> float:
    ordered = sorted(samples)
    index = max(int(len(ordered) * ratio) - 1, 0)
    return ordered[index]


def _prepare_preview_requests(count: int) -> list[tuple[str, dict[str, str]]]:
    from fastapi.testclient import TestClient

    client = TestClient(app)
    prepared: list[tuple[str, dict[str, str]]] = []
    for index in range(count):
        user_id = f"preview-perf-{index}"
        upload_id = f"preview-perf-upload-{index}"
        seed_completed_upload(upload_id=upload_id, owner_user_id=user_id)
        seed_detection(upload_id=upload_id, owner_user_id=user_id)
        save_configuration(client, upload_id=upload_id, owner_user_id=user_id)
        prepared.append((upload_id, fake_auth_header(user_id, tier="pro")))
    return prepared


async def _run_concurrent_preview_creation(prepared: list[tuple[str, dict[str, str]]]) -> list[float]:
    transport = httpx.ASGITransport(app=app)
    semaphore = asyncio.Semaphore(25)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        async def send_request(upload_id: str, headers: dict[str, str]) -> float:
            async with semaphore:
                started = perf_counter()
                response = await async_client.post("/v1/previews", headers=headers, json={"upload_id": upload_id})
                elapsed = perf_counter() - started
                assert response.status_code == 200
                return elapsed

        return list(await asyncio.gather(*(send_request(upload_id, headers) for upload_id, headers in prepared)))


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_phase2_store()


def test_preview_generation_meets_latency_target_envelope() -> None:
    prepared = _prepare_preview_requests(60)
    samples = asyncio.run(_run_concurrent_preview_creation(prepared))

    assert len(samples) == 60
    assert _percentile(samples, 0.95) < 6.0
