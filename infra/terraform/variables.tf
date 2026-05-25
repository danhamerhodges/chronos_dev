variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "notification_channels" {
  description = "Alert notification channel IDs (PagerDuty/Slack/email) created in Cloud Monitoring."
  type        = list(string)
  default     = []
}

variable "runtime_service_accounts" {
  description = "Service accounts used by Cloud Run services/jobs."
  type        = list(string)
  default     = []
}

variable "deploy_service_accounts" {
  description = "Service accounts allowed to deploy Cloud Run revisions."
  type        = list(string)
  default     = []
}

variable "build_service_accounts" {
  description = "Service accounts used by Cloud Build source deploys."
  type        = list(string)
  default     = []
}

variable "metrics_namespace" {
  description = "Metric namespace prefix used by the application."
  type        = string
  default     = "chronos"
}

variable "manage_manifest_lifecycle_rules" {
  description = "When true, Terraform manages GCS lifecycle rules for SEC-005 manifest retention prefixes. Import and review existing bucket config before enabling."
  type        = bool
  default     = false
}

variable "manage_manifest_object_mutator_iam" {
  description = "When true, Terraform manages the SEC-005 hosted manifest metadata/delete custom role and conditional bucket binding. Import existing hosted IAM before enabling."
  type        = bool
  default     = false
}

variable "manage_storage_data_access_audit_config" {
  description = "When true, Terraform authoritatively manages Cloud Storage Data Access audit logging for SEC-005 lifecycle deletion proof. Inspect existing audit configs before enabling."
  type        = bool
  default     = false
}

variable "manage_sec002_encryption_checks" {
  description = "When true, enables SEC-002 encryption verification scaffolding. Keep disabled unless live GCP credentials and explicit hosted evidence collection are available."
  type        = bool
  default     = false
}

variable "manifest_lifecycle_bucket_name" {
  description = "Existing GCS bucket name for transformation manifests when SEC-005 lifecycle management is enabled."
  type        = string
  default     = ""
}

variable "manifest_lifecycle_bucket_location" {
  description = "Location of the existing manifest bucket when lifecycle management is enabled."
  type        = string
  default     = "US"
}

variable "manifest_object_mutator_service_account" {
  description = "Cloud Run service account email that receives SEC-005 manifest object metadata/delete permissions when manage_manifest_object_mutator_iam is enabled."
  type        = string
  default     = ""
}

variable "manifest_object_mutator_role_id" {
  description = "Custom project role ID for SEC-005 manifest object metadata/delete permissions."
  type        = string
  default     = "chronosManifestObjectMutator"
}
