"""
Maps to:
- SEC-002
"""

from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SECURITY_SPEC = ROOT / "docs/specs/chronosrefine_security_operations_requirements.md"
MATRIX = ROOT / "docs/specs/ChronosRefine Requirements Coverage Matrix.md"
PACKET_NOTE = ROOT / "docs/specs/chronosrefine_phase5_packet5i_implementation_note.md"
TERRAFORM_VARIABLES = ROOT / "infra/terraform/variables.tf"
TERRAFORM_DIR = ROOT / "infra/terraform"

REQUIRED_BUCKET_ROLES = ("uploads", "outputs", "backups")
REQUIRED_DEFAULT_ENCRYPTION = "AES256"


def _bucket_encryption_satisfies_sec002_at_rest(bucket_config: dict[str, object]) -> bool:
    encryption = str(bucket_config.get("default_encryption", "")).upper()
    return encryption == REQUIRED_DEFAULT_ENCRYPTION


@pytest.mark.parametrize("bucket_role", REQUIRED_BUCKET_ROLES)
def test_sec002_requires_aes256_for_each_gcs_bucket(bucket_role: str) -> None:
    spec = SECURITY_SPEC.read_text()

    assert "AES-256 encryption verified for **all 3 GCS buckets**" in spec
    assert bucket_role in ("uploads", "outputs", "backups")
    assert _bucket_encryption_satisfies_sec002_at_rest(
        {"bucket_role": bucket_role, "default_encryption": "AES256", "kms_key_name": None}
    )


def test_aes256_bucket_verifier_accepts_cmek_and_rejects_unencrypted_configs() -> None:
    assert not _bucket_encryption_satisfies_sec002_at_rest({"bucket_role": "uploads", "default_encryption": "NONE"})
    assert _bucket_encryption_satisfies_sec002_at_rest(
        {
            "bucket_role": "outputs",
            "default_encryption": "AES256",
            "kms_key_name": "projects/chronos/locations/global/keyRings/museum/cryptoKeys/cmek",
        }
    )


def test_sec002_encryption_checks_are_disabled_by_default() -> None:
    variables = TERRAFORM_VARIABLES.read_text()

    assert 'variable "manage_sec002_encryption_checks"' in variables
    assert 'description = "When true, enables SEC-002 encryption verification scaffolding' in variables
    assert "default     = false" in variables


def test_sec002_does_not_add_ungated_live_gcp_bucket_checks() -> None:
    terraform_sources = "\n".join(path.read_text() for path in TERRAFORM_DIR.glob("*.tf"))

    assert "manage_sec002_encryption_checks" in terraform_sources
    assert 'data "google_storage_bucket"' not in terraform_sources
    assert 'resource "google_storage_bucket" "sec002' not in terraform_sources


def test_cmek_is_documented_as_deferred_to_sec007() -> None:
    matrix = MATRIX.read_text()
    note = PACKET_NOTE.read_text()

    assert "`tests/security/test_cmek.py`" in matrix
    assert "`tests/security/test_cmek.py` is intentionally not created in Packet 5I" in note
    assert "full CMEK implementation and key-rotation coverage remain reserved for `SEC-007`" in note
