terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.33"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  labels = merge({ app = "rsrssr" }, var.labels)
  artifact_location = var.artifact_registry_location != "" ? var.artifact_registry_location : var.region
}

resource "google_project_service" "enabled" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "iam.googleapis.com",
    "run.googleapis.com",
    "storage.googleapis.com",
  ])
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "db" {
  name          = var.db_bucket_name != "" ? var.db_bucket_name : "${var.project_id}-rsrssr-db"
  project       = var.project_id
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true
  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      num_newer_versions = 10
    }
  }

  labels = local.labels
}

resource "google_service_account" "app" {
  account_id   = "rsrssr-app"
  display_name = "RSRSSR runtime"
}

resource "google_service_account" "scheduler" {
  account_id   = "rsrssr-scheduler"
  display_name = "RSRSSR Cloud Scheduler"
}

resource "google_storage_bucket_iam_member" "app" {
  bucket = google_storage_bucket.db.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.app.email}"
}

resource "google_project_iam_member" "artifact_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.app.email}"
}

resource "google_artifact_registry_repository" "app" {
  location      = local.artifact_location
  repository_id = var.artifact_registry_repo
  format        = "DOCKER"
  description   = "Container images for RSRSSR"
  labels        = local.labels
}

locals {
  container_image = var.container_image != "" ? var.container_image : "${local.artifact_location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.app.repository_id}/rsrssr:latest"
}

resource "google_cloud_run_v2_service" "web" {
  name     = var.service_name
  location = var.region
  labels   = local.labels

  template {
    service_account        = google_service_account.app.email
    execution_environment  = "GEN2"
    timeout                = "60s"

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = local.container_image
      ports {
        container_port = 8080
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
      env {
        name  = "PORT"
        value = "8080"
      }
      env {
        name  = "RSRSSR_DB_PATH"
        value = "/data/rss_feeds.db"
      }
      volume_mounts {
        name       = "database"
        mount_path = "/data"
      }
    }

    volumes {
      name = "database"
      gcs {
        bucket = google_storage_bucket.db.name
      }
    }
  }

  ingress = "INGRESS_TRAFFIC_ALL"

  depends_on = [google_project_service.enabled]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.web.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_job" "update" {
  name     = var.job_name
  location = var.region
  labels   = local.labels

  template {
    parallelism  = 1
    task_count   = 1
    template {
      service_account       = google_service_account.app.email
      execution_environment = "GEN2"
      timeout               = "1200s"
      max_retries           = 1

      containers {
        image   = local.container_image
        command = ["python", "update.py"]
        env {
          name  = "RSRSSR_DB_PATH"
          value = "/data/rss_feeds.db"
        }
        volume_mounts {
          name       = "database"
          mount_path = "/data"
        }
        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
      }

      volumes {
        name = "database"
        gcs {
          bucket = google_storage_bucket.db.name
        }
      }
    }
  }

  depends_on = [google_project_service.enabled]
}

resource "google_cloud_run_v2_job_iam_member" "scheduler" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.update.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_scheduler_job" "update" {
  name        = "${var.job_name}-schedule"
  description = "Trigger the RSRSSR update Cloud Run job"
  schedule    = var.update_schedule
  time_zone   = var.time_zone
  region      = var.region

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/${google_cloud_run_v2_job.update.name}:run"
    body        = base64encode("{}")

    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }

    headers = {
      "Content-Type" = "application/json"
    }
  }

  depends_on = [
    google_project_service.enabled,
    google_cloud_run_v2_job_iam_member.scheduler,
  ]
}

output "service_url" {
  description = "Public URL for the RSRSSR web interface"
  value       = google_cloud_run_v2_service.web.uri
}

output "database_bucket" {
  description = "Bucket that stores the SQLite database"
  value       = google_storage_bucket.db.name
}

output "artifact_repository" {
  description = "Artifact Registry repository that should host the container image"
  value       = google_artifact_registry_repository.app.id
}
