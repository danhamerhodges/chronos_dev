"""Maps to: ENG-005"""

from fastapi.testclient import TestClient

from app.main import app
from app.db.phase2_store import JobRepository
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import valid_job_request

client = TestClient(app)


def test_all_fidelity_tiers_persist_effective_profile() -> None:
    scenarios = [
        ("Enhance", 0.30, "Subtle"),
        ("Restore", 0.15, "Matched"),
        ("Conserve", 0.05, "Heavy"),
    ]

    for tier, hallucination_limit, grain in scenarios:
        response = client.post(
            "/v1/jobs",
            headers=fake_auth_header(f"user-{tier.lower()}", tier="pro"),
            json=valid_job_request(
                fidelity_tier=tier,
                era_profile={
                    **valid_job_request()["era_profile"],
                    "mode": tier,
                    "hallucination_limit": hallucination_limit,
                    "artifact_policy": {
                        **valid_job_request()["era_profile"]["artifact_policy"],
                        "grain_intensity": grain,
                    },
                },
            ),
        )

        assert response.status_code == 202
        payload = response.json()
        assert payload["fidelity_tier"] == tier
        assert payload["effective_fidelity_tier"] == tier
        assert payload["reproducibility_mode"] == "perceptual_equivalence"
        job = JobRepository().get_job(
            payload["job_id"],
            owner_user_id=f"user-{tier.lower()}",
            access_token=f"test-token-for-user-{tier.lower()}",
        )
        assert job is not None
        assert job["effective_fidelity_profile"]["grain_preset"] == grain


def test_tier_breaking_override_is_rejected() -> None:
    response = client.post(
        "/v1/jobs",
        headers=fake_auth_header("invalid-tier-user", tier="pro"),
        json=valid_job_request(
            fidelity_tier="Restore",
            config={"fidelity_overrides": {"hallucination_limit": 0.2}},
        ),
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid Fidelity Override"
