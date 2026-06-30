variable "project_id" {
  type        = string
  description = "GCP project ID that owns the Artifact Registry repository."
}

variable "region" {
  type        = string
  description = "GCP region (location) for the repository."
}

variable "repository_id" {
  type        = string
  description = "Repository ID (name) for the Docker repository."
}

variable "description" {
  type        = string
  description = "Human-readable description of the repository."
  default     = "Application container images"
}

variable "keep_recent_count" {
  type        = number
  description = "Number of most-recent versions to keep under the cleanup policy."
  default     = 10
}

variable "delete_untagged_older_than_days" {
  type        = number
  description = "Delete untagged images older than this many days."
  default     = 30
}
