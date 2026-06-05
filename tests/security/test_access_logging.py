"""
Maps to:
- SEC-004
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _resource_start(terraform: str, resource_header: str) -> int:
    start = terraform.find(resource_header)
    assert start != -1, f"missing Terraform resource: {resource_header}"
    return start


def _resource_block(terraform: str, resource_header: str) -> str:
    start = _resource_start(terraform, resource_header)
    next_resource = terraform.find('\nresource "', start + len(resource_header))
    end = next_resource if next_resource != -1 else len(terraform)
    return terraform[start:end]


def test_storage_data_access_audit_logging_is_declared_for_read_and_write() -> None:
    iam_tf = (ROOT / "infra" / "terraform" / "iam.tf").read_text(encoding="utf-8")
    audit_block = _resource_block(
        iam_tf,
        'resource "google_project_iam_audit_config" "storage_data_access"',
    )

    assert "count = var.manage_storage_data_access_audit_config ? 1 : 0" in audit_block
    assert 'service = "storage.googleapis.com"' in audit_block
    assert 'log_type = "DATA_READ"' in audit_block
    assert 'log_type = "DATA_WRITE"' in audit_block


def test_storage_data_access_audit_logging_is_gated_before_hosted_apply() -> None:
    variables_tf = (ROOT / "infra" / "terraform" / "variables.tf").read_text(encoding="utf-8")
    iam_tf = (ROOT / "infra" / "terraform" / "iam.tf").read_text(encoding="utf-8")

    assert 'variable "manage_storage_data_access_audit_config"' in variables_tf
    variable_match = re.search(
        r'variable\s+"manage_storage_data_access_audit_config"\s*\{(?P<body>.*?)\n\}',
        variables_tf,
        re.DOTALL,
    )
    assert variable_match is not None
    assert re.search(r"default\s*=\s*false", variable_match.group("body")) is not None
    resource_start = _resource_start(iam_tf, 'resource "google_project_iam_audit_config" "storage_data_access"')
    preflight_comment = iam_tf[:resource_start].rsplit("\n\n", maxsplit=1)[-1]
    assert "authoritative" in preflight_comment
    assert "gcloud projects get-iam-policy" in preflight_comment
