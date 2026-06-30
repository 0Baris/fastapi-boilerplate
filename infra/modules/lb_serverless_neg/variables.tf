variable "project_id" {
  type        = string
  description = "GCP project ID that owns the load balancer resources."
}

variable "region" {
  type        = string
  description = "Region of the Cloud Run service the serverless NEG points at."
}

variable "name_prefix" {
  type        = string
  description = "Prefix applied to every load balancer resource name."
}

variable "domain" {
  type        = string
  description = "Fully qualified domain served by the load balancer (e.g. api.example.com)."
}

variable "cloud_run_service_name" {
  type        = string
  description = "Name of the Cloud Run service backing the serverless NEG."
}

variable "enable_cdn" {
  type        = bool
  description = "Whether Cloud CDN is enabled on the backend service."
  default     = false
}
