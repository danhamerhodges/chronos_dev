resource "google_monitoring_dashboard" "chronos_phase1" {
  # Cloud Monitoring API normalizes dashboard JSON (adds/removes implicit fields),
  # which otherwise causes perpetual no-op drift in plan output.
  lifecycle {
    ignore_changes = [dashboard_json]
  }

  dashboard_json = jsonencode({
    displayName = "ChronosRefine Phase 1 - Service Health"
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          xPos   = 0
          yPos   = 0
          width  = 6
          height = 4
          widget = {
            title = "Cloud Run Request Count"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\""
                    }
                  }
                  plotType = "LINE"
                }
              ]
              yAxis = {
                label = "req/s"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          xPos   = 6
          yPos   = 0
          width  = 6
          height = 4
          widget = {
            title = "App Service Up Gauge"
            scorecard = {
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"custom.googleapis.com/${var.metrics_namespace}/service_up\""
                }
              }
              gaugeView = {
                lowerBound = 0
                upperBound = 1
              }
            }
          }
        },
        {
          xPos   = 0
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Runtime Queue Depth"
            scorecard = {
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"custom.googleapis.com/${var.metrics_namespace}/runtime_gauge\" metric.labels.name=\"queue_depth\""
                }
              }
              gaugeView = {
                lowerBound = 0
                upperBound = 100
              }
            }
          }
        },
        {
          xPos   = 6
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Segment Cache Events"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"custom.googleapis.com/${var.metrics_namespace}/segment_cache_events_total\""
                    }
                  }
                  plotType = "STACKED_BAR"
                }
              ]
              yAxis = {
                label = "events"
                scale = "LINEAR"
              }
            }
          }
        }
      ]
    }
  })
}
