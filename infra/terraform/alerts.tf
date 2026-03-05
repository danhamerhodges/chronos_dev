resource "google_monitoring_alert_policy" "error_rate_high" {
  display_name = "ChronosRefine - API Error Rate High"
  combiner     = "OR"

  conditions {
    display_name = "Cloud Run 5xx ratio > 1%"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\" metric.labels.response_code_class=\"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.01

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    mime_type = "text/markdown"
    content   = "Error rate breached SLO. Check `/v1/metrics`, Cloud Run logs, and rollback runbook."
  }
}
