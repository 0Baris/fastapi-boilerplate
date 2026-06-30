variable "project_id" {
  type        = string
  description = "GCP project ID that owns the Cloud Run job."
}

variable "region" {
  type        = string
  description = "GCP region (location) for the job."
}

variable "job_name" {
  type        = string
  description = "Name of the Cloud Run job."
}

variable "image" {
  type        = string
  description = "Initial container image. Drift is ignored after first deploy (Cloud Build owns the image)."
}

variable "command" {
  type        = list(string)
  description = "Container entrypoint command. Empty list uses the image default."
  default     = []
}

variable "cpu" {
  type        = string
  description = "CPU limit per task (e.g. \"1\")."
  default     = "1"
}

variable "memory" {
  type        = string
  description = "Memory limit per task (e.g. \"512Mi\", \"1Gi\")."
  default     = "512Mi"
}

variable "service_account" {
  type        = string
  description = "Email of the service account the job runs as."
}

variable "egress_subnet_id" {
  type        = string
  description = "Subnet ID for Direct VPC Egress (projects/.../subnetworks/<name> form)."
}

variable "vpc_egress" {
  type        = string
  description = "VPC egress setting (PRIVATE_RANGES_ONLY or ALL_TRAFFIC)."
  default     = "PRIVATE_RANGES_ONLY"
}

variable "env" {
  type        = map(string)
  description = "Plain (non-secret) environment variables."
  default     = {}
}

variable "secret_env" {
  type = map(object({
    secret  = string
    version = optional(string, "latest")
  }))
  description = "Environment variables sourced from Secret Manager: env var name => { secret, version }."
  default     = {}
}

variable "max_retries" {
  type        = number
  description = "Maximum retries per task before the execution is marked failed."
  default     = 1
}

variable "task_timeout_seconds" {
  type        = number
  description = "Per-task timeout in seconds."
  default     = 600
}
