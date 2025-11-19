variable "project_id" {
  description = "ID of the Google Cloud project"
  type        = string
}

variable "region" {
  description = "Region to deploy Cloud Run and Cloud Scheduler resources"
  type        = string
  default     = "us-central1"
}

variable "artifact_registry_location" {
  description = "Region/loc for Artifact Registry (defaults to region when empty)"
  type        = string
  default     = ""
}

variable "artifact_registry_repo" {
  description = "Name of the Artifact Registry repository"
  type        = string
  default     = "rsrssr"
}

variable "container_image" {
  description = "Fully qualified container image to deploy (defaults to repo-created path)"
  type        = string
  default     = ""
}

variable "service_name" {
  description = "Name for the Cloud Run service"
  type        = string
  default     = "rsrssr-web"
}

variable "job_name" {
  description = "Name for the Cloud Run job that runs update.py"
  type        = string
  default     = "rsrssr-update"
}

variable "db_bucket_name" {
  description = "Optional override for the Cloud Storage bucket name"
  type        = string
  default     = ""
}

variable "update_schedule" {
  description = "Cron schedule for Cloud Scheduler"
  type        = string
  default     = "0 */6 * * *"
}

variable "time_zone" {
  description = "IANA time zone for the scheduler"
  type        = string
  default     = "Etc/UTC"
}

variable "labels" {
  description = "Additional resource labels"
  type        = map(string)
  default     = {}
}
