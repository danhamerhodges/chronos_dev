terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  project_name          = "chronosrefine"
  source_deploy_buckets = length(var.deploy_source_buckets) > 0 ? var.deploy_source_buckets : ["run-sources-${var.project_id}-${var.region}"]
  deploy_bucket_bindings = {
    for pair in setproduct(toset(var.deploy_service_accounts), toset(local.source_deploy_buckets)) :
    "${pair[0]}|${pair[1]}" => {
      service_account = pair[0]
      bucket          = pair[1]
    }
  }
}
