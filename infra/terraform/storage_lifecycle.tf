# google_storage_bucket lifecycle configuration is authoritative for the bucket.
# Before hosted apply, import the existing bucket and inspect current rules:
# gcloud storage buckets describe gs://BUCKET --format=json
resource "google_storage_bucket" "manifest_retention" {
  count = var.manage_manifest_lifecycle_rules ? 1 : 0

  name          = var.manifest_lifecycle_bucket_name
  location      = var.manifest_lifecycle_bucket_location
  force_destroy = false

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = var.manifest_lifecycle_bucket_name != ""
      error_message = "manifest_lifecycle_bucket_name must be set before enabling SEC-005 manifest lifecycle management."
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age            = 7
      matches_prefix = ["manifests/7d/"]
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age            = 90
      matches_prefix = ["manifests/90d/"]
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age            = 365
      matches_prefix = ["manifests/365d/"]
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age            = 1825
      matches_prefix = ["manifests/1825d/"]
    }
  }
}
