output "project_id" {
  value = var.project_id
}

output "monitoring_dashboard_id" {
  value = google_monitoring_dashboard.chronos_phase1.id
}

output "error_rate_alert_policy_id" {
  value = google_monitoring_alert_policy.error_rate_high.id
}
