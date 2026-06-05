"""
Maps to:
- SEC-004
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_iam_policies_are_managed_by_terraform_with_service_accounts() -> None:
    iam_tf = (ROOT / "infra" / "terraform" / "iam.tf").read_text(encoding="utf-8")

    assert 'resource "google_project_iam_member" "runtime_log_writer"' in iam_tf
    assert 'resource "google_project_iam_member" "deploy_run_admin"' in iam_tf
    assert 'member   = "serviceAccount:${each.value}"' in iam_tf
    assert "user:" not in iam_tf
    assert "roles/owner" not in iam_tf
    assert "roles/editor" not in iam_tf


def test_manifest_mutator_role_is_narrow_and_prefix_conditioned() -> None:
    iam_tf = (ROOT / "infra" / "terraform" / "iam.tf").read_text(encoding="utf-8")

    assert 'resource "google_project_iam_custom_role" "manifest_object_mutator"' in iam_tf
    assert '"storage.objects.delete"' in iam_tf
    assert '"storage.objects.update"' in iam_tf
    assert "storage.objects.get" not in iam_tf
    assert "storage.objects.list" not in iam_tf
    assert "resource.name.startsWith" in iam_tf
    assert "/objects/manifests/" in iam_tf
