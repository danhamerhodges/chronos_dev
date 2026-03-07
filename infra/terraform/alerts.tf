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

resource "google_monitoring_alert_policy" "processing_time_slo_breach" {
  display_name = "ChronosRefine - Processing Time SLO Breach"
  combiner     = "OR"

  conditions {
    display_name = "Processing time p95 ratio > 1.0"
    condition_threshold {
      filter          = "metric.type=\"custom.googleapis.com/${var.metrics_namespace}/runtime_gauge\" metric.labels.name=\"slo_p95_ratio\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 1.0

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    mime_type = "text/markdown"
    content   = "Processing time SLO breach. Check `/v1/ops/runtime`, GPU warm pool, cache hit rate, and processing queue depth."
  }
}

resource "google_monitoring_alert_policy" "gpu_pool_exhaustion" {
  display_name = "ChronosRefine - GPU Pool Exhaustion"
  combiner     = "OR"

  conditions {
    display_name = "Busy instances saturate active warm pool"
    condition_threshold {
      filter          = "metric.type=\"custom.googleapis.com/${var.metrics_namespace}/runtime_gauge\" metric.labels.name=\"busy_instances\""
      duration        = "180s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    mime_type = "text/markdown"
    content   = "GPU pool saturation detected. Reconcile warm pool capacity and inspect dispatch backlog."
  }
}
