variable "project_id" {
  type        = string
  description = "GCP project ID that owns the network resources."
}

variable "region" {
  type        = string
  description = "GCP region for the regional subnets."
}

variable "vpc_name" {
  type        = string
  description = "Name of the custom-mode VPC network to create."
}

variable "subnet_name" {
  type        = string
  description = "Name of the primary regional subnet."
}

variable "subnet_cidr" {
  type        = string
  description = "Primary subnet IPv4 CIDR range (e.g. 10.0.0.0/24)."
}

variable "egress_subnet_name" {
  type        = string
  description = "Name of the Direct VPC Egress subnet used by Cloud Run."
}

variable "egress_subnet_cidr" {
  type        = string
  description = "Direct VPC Egress subnet IPv4 CIDR range (e.g. 10.0.1.0/28)."
}

variable "psa_range_name" {
  type        = string
  description = "Name of the PSA (Private Service Access) global address reservation."
}

variable "psa_prefix_length" {
  type        = number
  description = "Prefix length for the PSA-allocated range (e.g. 16)."
  default     = 16
}

variable "deny_all_egress_name" {
  type        = string
  description = "Name of the deny-all egress firewall rule."
}

variable "allow_egress_psa_name" {
  type        = string
  description = "Name of the firewall rule allowing runtime SA egress to the PSA range."
}

variable "runtime_sa_email" {
  type        = string
  description = "Runtime service account email targeted by the allow-egress-to-PSA firewall rule."
}

variable "db_port" {
  type        = number
  description = "PostgreSQL port allowed on egress to the PSA range."
  default     = 5432
}

variable "redis_port" {
  type        = number
  description = "Redis port allowed on egress to the PSA range."
  default     = 6379
}
