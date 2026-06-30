variable "project_id" {
  type        = string
  description = "GCP project ID that owns the Cloud Run service."
}

variable "region" {
  type        = string
  description = "GCP region (location) for the service."
}

variable "service_name" {
  type        = string
  description = "Name of the Cloud Run service."
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
  description = "CPU limit per container (e.g. \"1\", \"2\")."
  default     = "1"
}

variable "memory" {
  type        = string
  description = "Memory limit per container (e.g. \"512Mi\", \"1Gi\")."
  default     = "512Mi"
}

variable "cpu_idle" {
  type        = bool
  description = "If true, CPU is throttled when no requests are being served. Set false for always-on workers."
  default     = true
}

variable "min_instances" {
  type        = number
  description = "Minimum number of instances."
  default     = 0
}

variable "max_instances" {
  type        = number
  description = "Maximum number of instances."
  default     = 10
}

variable "ingress" {
  type        = string
  description = "Ingress setting (e.g. INGRESS_TRAFFIC_ALL, INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER, INGRESS_TRAFFIC_INTERNAL_ONLY)."
  default     = "INGRESS_TRAFFIC_ALL"
}

variable "service_account" {
  type        = string
  description = "Email of the service account the revisions run as."
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

variable "port" {
  type        = number
  description = "Container port the service listens on."
  default     = 8000
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

variable "allow_unauthenticated" {
  type        = bool
  description = "If true, grants allUsers the run.invoker role (public access)."
  default     = false
}

variable "startup_probe_path" {
  type        = string
  description = "HTTP path for the startup probe. Empty disables the probe."
  default     = ""
}

variable "liveness_probe_path" {
  type        = string
  description = "HTTP path for the liveness probe. Empty disables the probe."
  default     = ""
}

variable "timeout_seconds" {
  type        = number
  description = "Request timeout in seconds."
  default     = 300
}
