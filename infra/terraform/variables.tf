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
