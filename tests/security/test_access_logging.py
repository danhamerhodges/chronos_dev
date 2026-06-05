"""
Maps to:
- SEC-004
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_storage_data_access_audit_logging_is_declared_for_read_and_write() -> None:
    iam_tf = (ROOT / "infra" / "terraform" / "iam.tf").read_text(encoding="utf-8")

    assert 'resource "google_project_iam_audit_config" "storage_data_access"' in iam_tf
    assert 'service = "storage.googleapis.com"' in iam_tf
    assert 'log_type = "DATA_READ"' in iam_tf
    assert 'log_type = "DATA_WRITE"' in iam_tf


def test_storage_data_access_audit_logging_is_gated_before_hosted_apply() -> None:
    variables_tf = (ROOT / "infra" / "terraform" / "variables.tf").read_text(encoding="utf-8")
    iam_tf = (ROOT / "infra" / "terraform" / "iam.tf").read_text(encoding="utf-8")

    assert 'variable "manage_storage_data_access_audit_config"' in variables_tf
    assert "default     = false" in variables_tf
    assert "authoritative" in iam_tf
    assert "gcloud projects get-iam-policy" in iam_tf
