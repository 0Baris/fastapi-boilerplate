variable "project_id" {
  type        = string
  description = "GCP project ID that owns the secrets."
}

variable "region" {
  type        = string
  description = "GCP region for user-managed secret replicas."
}

variable "secret_names" {
  type        = list(string)
  description = "Secret IDs to create in Secret Manager. Values are populated out-of-band; never put secret values in Terraform."
}

variable "runtime_sa_email" {
  type        = string
  description = "Runtime service account email granted secretAccessor on each secret."
}
