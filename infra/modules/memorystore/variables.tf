variable "project_id" {
  type        = string
  description = "GCP project ID that owns the Memorystore instance."
}

variable "region" {
  type        = string
  description = "GCP region for the Memorystore instance."
}

variable "instance_name" {
  type        = string
  description = "Name of the Memorystore (Redis) instance."
}

variable "tier" {
  type        = string
  description = "Service tier (BASIC or STANDARD_HA)."
  default     = "BASIC"
}

variable "memory_size_gb" {
  type        = number
  description = "Redis memory size in GB."
  default     = 1
}

variable "redis_version" {
  type        = string
  description = "Redis engine version (e.g. REDIS_7_2)."
  default     = "REDIS_7_2"
}

variable "authorized_network" {
  type        = string
  description = "VPC network ID authorized to reach the instance via PSA."
}

variable "auth_enabled" {
  type        = bool
  description = "Whether AUTH (password) is required to connect."
  default     = true
}

variable "transit_encryption_mode" {
  type        = string
  description = "Transit encryption mode (DISABLED or SERVER_AUTHENTICATION)."
  default     = "SERVER_AUTHENTICATION"
}
