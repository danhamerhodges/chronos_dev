"""Packet 4D deletion-proof delivery routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.api.contracts import DeletionProofResponse
from app.api.dependencies import AuthenticatedUser, apply_rate_limit, require_permission
from app.services.job_service import JobService

router = APIRouter()
_job_service = JobService()


@router.get("/v1/deletion-proofs/{proof_id}", response_model=DeletionProofResponse)
def get_deletion_proof(
    proof_id: str,
    response: Response,
    user: AuthenticatedUser = Depends(require_permission("jobs:read")),
) -> DeletionProofResponse:
    apply_rate_limit(user, "/v1/deletion-proofs/{proof_id}")
    response.headers["Cache-Control"] = "private, no-store"
    payload = _job_service.get_deletion_proof(
        proof_id,
        owner_user_id=user.user_id,
        access_token=user.access_token,
    )
    return DeletionProofResponse.model_validate(payload)
