resource "google_monitoring_dashboard" "chronos_phase1" {
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
        }
      ]
    }
  })
}
