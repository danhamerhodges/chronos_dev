resource "google_project_iam_member" "runtime_log_writer" {
  for_each = toset(var.runtime_service_accounts)
  project  = var.project_id
  role     = "roles/logging.logWriter"
  member   = "serviceAccount:${each.value}"
}

resource "google_project_iam_member" "runtime_metric_writer" {
  for_each = toset(var.runtime_service_accounts)
  project  = var.project_id
  role     = "roles/monitoring.metricWriter"
  member   = "serviceAccount:${each.value}"
}

resource "google_project_iam_member" "runtime_trace_agent" {
  for_each = toset(var.runtime_service_accounts)
  project  = var.project_id
  role     = "roles/cloudtrace.agent"
  member   = "serviceAccount:${each.value}"
}

resource "google_project_iam_member" "deploy_run_admin" {
  for_each = toset(var.deploy_service_accounts)
  project  = var.project_id
  role     = "roles/run.admin"
  member   = "serviceAccount:${each.value}"
}

resource "google_project_iam_member" "deploy_service_account_user" {
  for_each = toset(var.deploy_service_accounts)
  project  = var.project_id
  role     = "roles/iam.serviceAccountUser"
  member   = "serviceAccount:${each.value}"
}

resource "google_project_iam_member" "deploy_cloudbuild_editor" {
  for_each = toset(var.deploy_service_accounts)
  project  = var.project_id
  role     = "roles/cloudbuild.builds.editor"
  member   = "serviceAccount:${each.value}"
}

resource "google_project_iam_member" "deploy_artifactregistry_reader" {
  for_each = toset(var.deploy_service_accounts)
  project  = var.project_id
  role     = "roles/artifactregistry.reader"
  member   = "serviceAccount:${each.value}"
}

resource "google_project_iam_member" "deploy_serviceusage_consumer" {
  for_each = toset(var.deploy_service_accounts)
  project  = var.project_id
  role     = "roles/serviceusage.serviceUsageConsumer"
  member   = "serviceAccount:${each.value}"
}

resource "google_project_iam_member" "deploy_storage_bucket_viewer" {
  for_each = toset(var.deploy_service_accounts)
  project  = var.project_id
  role     = "roles/storage.bucketViewer"
  member   = "serviceAccount:${each.value}"
}

resource "google_project_iam_member" "deploy_storage_object_viewer" {
  for_each = toset(var.deploy_service_accounts)
  project  = var.project_id
  role     = "roles/storage.objectViewer"
  member   = "serviceAccount:${each.value}"
}

resource "google_project_iam_member" "deploy_storage_object_creator" {
  for_each = toset(var.deploy_service_accounts)
  project  = var.project_id
  role     = "roles/storage.objectCreator"
  member   = "serviceAccount:${each.value}"
}

resource "google_project_iam_custom_role" "manifest_object_mutator" {
  count = var.manage_manifest_object_mutator_iam ? 1 : 0

  project     = var.project_id
  role_id     = var.manifest_object_mutator_role_id
  title       = "Chronos Manifest Object Mutator"
  description = "Packet 5K-D1 least-privilege role for hosted manifest metadata patch and 0-day delete on the manifest bucket."
  permissions = [
    "storage.objects.delete",
    "storage.objects.update",
  ]
  stage = "GA"

  lifecycle {
    precondition {
      condition     = var.manifest_object_mutator_service_account != ""
      error_message = "manifest_object_mutator_service_account must be set before enabling SEC-005 manifest object mutator IAM."
    }

    precondition {
      condition     = var.manifest_lifecycle_bucket_name != ""
      error_message = "manifest_lifecycle_bucket_name must be set before enabling SEC-005 manifest object mutator IAM."
    }
  }
}

resource "google_storage_bucket_iam_member" "runtime_manifest_object_mutator" {
  count = var.manage_manifest_object_mutator_iam ? 1 : 0

  bucket = var.manifest_lifecycle_bucket_name
  role   = google_project_iam_custom_role.manifest_object_mutator[0].name
  member = "serviceAccount:${var.manifest_object_mutator_service_account}"

  condition {
    title       = "packet5kd1ManifestObjectsOnly"
    description = "Limit Packet 5K-D1 hosted manifest metadata/delete repair to objects under manifests/."
    expression  = "resource.name.startsWith(\"projects/_/buckets/${var.manifest_lifecycle_bucket_name}/objects/manifests/\")"
  }
}

resource "google_project_iam_member" "build_source_object_viewer" {
  for_each = toset(var.build_service_accounts)
  project  = var.project_id
  role     = "roles/storage.objectViewer"
  member   = "serviceAccount:${each.value}"
}

resource "google_project_iam_member" "build_run_builder" {
  for_each = toset(var.build_service_accounts)
  project  = var.project_id
  role     = "roles/run.builder"
  member   = "serviceAccount:${each.value}"
}

# google_project_iam_audit_config is authoritative for this service. Before
# hosted apply, inspect existing audit configs with:
# gcloud projects get-iam-policy PROJECT_ID --format=json
resource "google_project_iam_audit_config" "storage_data_access" {
  count = var.manage_storage_data_access_audit_config ? 1 : 0

  project = var.project_id
  service = "storage.googleapis.com"

  audit_log_config {
    log_type = "DATA_READ"
  }

  audit_log_config {
    log_type = "DATA_WRITE"
  }
}
