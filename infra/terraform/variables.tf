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
