variable "project_id" {
  type        = string
  description = "GCP project ID that owns the Cloud SQL instance."
}

variable "region" {
  type        = string
  description = "GCP region for the Cloud SQL instance."
}

variable "instance_name" {
  type        = string
  description = "Name of the Cloud SQL instance."
}

variable "database_version" {
  type        = string
  description = "Cloud SQL PostgreSQL version (e.g. POSTGRES_16)."
  default     = "POSTGRES_16"
}

variable "tier" {
  type        = string
  description = "Machine tier for the instance (e.g. db-g1-small, db-custom-2-7680)."
  default     = "db-g1-small"
}

variable "edition" {
  type        = string
  description = "Cloud SQL edition (ENTERPRISE or ENTERPRISE_PLUS)."
  default     = "ENTERPRISE"
}

variable "disk_size" {
  type        = number
  description = "Data disk size in GB."
  default     = 10
}

variable "disk_type" {
  type        = string
  description = "Data disk type (PD_SSD or PD_HDD)."
  default     = "PD_SSD"
}

variable "availability_type" {
  type        = string
  description = "Availability type (ZONAL or REGIONAL for HA)."
  default     = "ZONAL"
}

variable "ssl_mode" {
  type        = string
  description = "SSL enforcement mode for connections."
  default     = "ENCRYPTED_ONLY"
}

variable "deletion_protection" {
  type        = bool
  description = "Whether the instance is protected from deletion."
  default     = true
}

variable "vpc_self_link" {
  type        = string
  description = "Self link of the VPC the instance attaches to for private IP."
}

variable "database_name" {
  type        = string
  description = "Name of the application database to create."
}

variable "db_user" {
  type        = string
  description = "Name of the database user to create."
}

variable "db_password" {
  type        = string
  description = "Password for the database user. Supply out-of-band; never commit a real value."
  sensitive   = true
}
