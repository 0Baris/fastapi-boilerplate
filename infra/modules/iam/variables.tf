variable "project_id" {
  type        = string
  description = "GCP project ID that owns the service accounts."
}

variable "runtime_sa_account_id" {
  type        = string
  description = "Account ID (local part of the email) for the runtime service account."
}

variable "runtime_sa_display_name" {
  type        = string
  description = "Display name for the runtime service account."
  default     = "Application runtime"
}

variable "cicd_sa_account_id" {
  type        = string
  description = "Account ID (local part of the email) for the CI/CD service account."
}

variable "cicd_sa_display_name" {
  type        = string
  description = "Display name for the CI/CD service account."
  default     = "CI/CD deploy"
}

variable "runtime_bucket_names" {
  type        = list(string)
  description = "GCS bucket names the runtime SA gets object access on. Empty = no bucket-scoped grant."
  default     = []
}
