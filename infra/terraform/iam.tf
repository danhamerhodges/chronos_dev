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

resource "google_project_iam_member" "deploy_storage_admin" {
  for_each = toset(var.deploy_service_accounts)
  project  = var.project_id
  role     = "roles/storage.admin"
  member   = "serviceAccount:${each.value}"
}

resource "google_project_iam_member" "deploy_serviceusage_consumer" {
  for_each = toset(var.deploy_service_accounts)
  project  = var.project_id
  role     = "roles/serviceusage.serviceUsageConsumer"
  member   = "serviceAccount:${each.value}"
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
