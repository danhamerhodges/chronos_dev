"""
Maps to:
- SEC-004
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
TERRAFORM_DIR = ROOT / "infra" / "terraform"


def _terraform_assignments(terraform: str, name: str) -> list[str]:
    return re.findall(rf'^\s*{re.escape(name)}\s*=\s*"([^"]+)"', terraform, re.MULTILINE)


def _resource_start(terraform: str, resource_header: str) -> int:
    start = terraform.find(resource_header)
    assert start != -1, f"missing Terraform resource: {resource_header}"
    return start


def test_terraform_security_sources_are_fmt_valid_when_terraform_is_available() -> None:
    terraform = shutil.which("terraform")
    if terraform is None:
        pytest.skip("terraform CLI is not installed")

    proc = subprocess.run(
        [terraform, "fmt", "-check", "-recursive"],
        cwd=TERRAFORM_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_iam_policies_are_managed_by_terraform_with_service_accounts() -> None:
    iam_tf = (ROOT / "infra" / "terraform" / "iam.tf").read_text(encoding="utf-8")
    member_assignments = _terraform_assignments(iam_tf, "member")
    role_assignments = _terraform_assignments(iam_tf, "role")

    assert 'resource "google_project_iam_member" "runtime_log_writer"' in iam_tf
    assert 'resource "google_project_iam_member" "deploy_run_admin"' in iam_tf
    assert 'member   = "serviceAccount:${each.value}"' in iam_tf
    assert member_assignments
    assert all(not member.startswith("user:") for member in member_assignments)
    assert "roles/owner" not in role_assignments
    assert "roles/editor" not in role_assignments


def test_manifest_mutator_role_is_narrow_and_prefix_conditioned() -> None:
    iam_tf = (ROOT / "infra" / "terraform" / "iam.tf").read_text(encoding="utf-8")
    role_start = _resource_start(iam_tf, 'resource "google_project_iam_custom_role" "manifest_object_mutator"')
    binding_start = _resource_start(
        iam_tf,
        'resource "google_storage_bucket_iam_member" "runtime_manifest_object_mutator"',
    )
    role_block = iam_tf[role_start:binding_start]
    binding_end = _resource_start(iam_tf, 'resource "google_project_iam_member" "build_source_object_viewer"')
    binding_block = iam_tf[binding_start:binding_end]

    assert '"storage.objects.delete"' in role_block
    assert '"storage.objects.update"' in role_block
    assert "storage.objects.get" not in role_block
    assert "storage.objects.list" not in role_block
    assert "resource.name.startsWith" in binding_block
    assert "/objects/manifests/" in binding_block
