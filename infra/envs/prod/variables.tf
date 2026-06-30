######################################################################
# Project / location
######################################################################

variable "project_id" {
  type        = string
  description = "GCP project ID for the whole stack."
}

variable "region" {
  type        = string
  description = "Primary GCP region (e.g. us-central1)."
}

variable "zone" {
  type        = string
  description = "Default GCP zone within the region (e.g. us-central1-a)."
}

######################################################################
# Network
######################################################################

variable "vpc_name" {
  type        = string
  description = "Name of the custom-mode VPC network."
  default     = "app-vpc"
}

variable "subnet_name" {
  type        = string
  description = "Name of the primary regional subnet."
  default     = "app-primary"
}

variable "subnet_cidr" {
  type        = string
  description = "Primary subnet IPv4 CIDR (e.g. 10.0.0.0/24)."
}

variable "egress_subnet_name" {
  type        = string
  description = "Name of the Direct VPC Egress subnet."
  default     = "app-egress"
}

variable "egress_subnet_cidr" {
  type        = string
  description = "Direct VPC Egress subnet IPv4 CIDR (e.g. 10.0.1.0/28)."
}

variable "psa_range_name" {
  type        = string
  description = "Name of the PSA global address reservation."
  default     = "app-psa-range"
}

variable "psa_prefix_length" {
  type        = number
  description = "Prefix length for the PSA-allocated range."
  default     = 16
}

variable "deny_all_egress_name" {
  type        = string
  description = "Name of the deny-all egress firewall rule."
  default     = "app-deny-all-egress"
}

variable "allow_egress_psa_name" {
  type        = string
  description = "Name of the allow-egress-to-PSA firewall rule."
  default     = "app-allow-egress-psa"
}

variable "db_port" {
  type        = number
  description = "PostgreSQL port opened on egress to the PSA range."
  default     = 5432
}

variable "redis_port" {
  type        = number
  description = "Redis port opened on egress to the PSA range."
  default     = 6379
}

######################################################################
# Cloud SQL (PostgreSQL)
######################################################################

variable "sql_instance_name" {
  type        = string
  description = "Name of the Cloud SQL instance."
  default     = "app-postgres"
}

variable "sql_database_version" {
  type        = string
  description = "Cloud SQL PostgreSQL version."
  default     = "POSTGRES_16"
}

variable "sql_tier" {
  type        = string
  description = "Cloud SQL machine tier."
  default     = "db-g1-small"
}

variable "sql_edition" {
  type        = string
  description = "Cloud SQL edition (ENTERPRISE or ENTERPRISE_PLUS)."
  default     = "ENTERPRISE"
}

variable "sql_disk_size" {
  type        = number
  description = "Cloud SQL data disk size in GB."
  default     = 10
}

variable "sql_disk_type" {
  type        = string
  description = "Cloud SQL data disk type (PD_SSD or PD_HDD)."
  default     = "PD_SSD"
}

variable "sql_availability_type" {
  type        = string
  description = "Cloud SQL availability type (ZONAL or REGIONAL)."
  default     = "ZONAL"
}

variable "sql_ssl_mode" {
  type        = string
  description = "Cloud SQL SSL enforcement mode."
  default     = "ENCRYPTED_ONLY"
}

variable "sql_deletion_protection" {
  type        = bool
  description = "Protect the Cloud SQL instance from deletion."
  default     = true
}

variable "db_name" {
  type        = string
  description = "Application database name."
  default     = "app"
}

variable "db_user" {
  type        = string
  description = "Application database user name."
  default     = "app"
}

variable "db_password" {
  type        = string
  description = "Application database user password. Supply via TF_VAR_db_password; never commit a real value."
  sensitive   = true
}

######################################################################
# Memorystore (Redis)
######################################################################

variable "redis_instance_name" {
  type        = string
  description = "Name of the Memorystore (Redis) instance."
  default     = "app-redis"
}

variable "redis_tier" {
  type        = string
  description = "Memorystore tier (BASIC or STANDARD_HA)."
  default     = "BASIC"
}

variable "redis_memory_size_gb" {
  type        = number
  description = "Memorystore memory size in GB."
  default     = 1
}

variable "redis_version" {
  type        = string
  description = "Redis engine version."
  default     = "REDIS_7_2"
}

variable "redis_auth_enabled" {
  type        = bool
  description = "Require AUTH on the Redis instance."
  default     = true
}

variable "redis_transit_encryption_mode" {
  type        = string
  description = <<-EOT
    Redis transit encryption: DISABLED or SERVER_AUTHENTICATION. Defaults to
    DISABLED — AUTH over the private VPC works out of the box. Set
    SERVER_AUTHENTICATION to enable TLS (the REDIS_URL then uses rediss:// +
    ssl_cert_reqs=none; pin the Memorystore CA on the client for full verification).
  EOT
  default     = "DISABLED"
}

######################################################################
# Secrets
######################################################################

variable "secret_names" {
  type        = list(string)
  description = "Secret IDs to create in Secret Manager. Values are populated out-of-band."
}

######################################################################
# IAM
######################################################################

variable "runtime_sa_account_id" {
  type        = string
  description = "Account ID for the runtime service account."
  default     = "app-runtime"
}

variable "cicd_sa_account_id" {
  type        = string
  description = "Account ID for the CI/CD service account."
  default     = "app-cicd"
}

variable "runtime_bucket_names" {
  type        = list(string)
  description = "GCS bucket names the runtime SA gets object access on. Empty = none."
  default     = []
}

######################################################################
# Artifact Registry
######################################################################

variable "ar_repo_name" {
  type        = string
  description = "Artifact Registry Docker repository ID."
  default     = "app"
}

variable "ar_keep_recent_count" {
  type        = number
  description = "Number of most-recent image versions to keep."
  default     = 10
}

variable "ar_delete_untagged_older_than_days" {
  type        = number
  description = "Delete untagged images older than this many days."
  default     = 30
}

######################################################################
# Container image
######################################################################

variable "image_name" {
  type        = string
  description = "Image name (within the Artifact Registry repo) for the application."
  default     = "app"
}

variable "image_tag" {
  type        = string
  description = "Image tag used to seed the initial deploy (Cloud Build owns it afterwards)."
  default     = "latest"
}

######################################################################
# Cloud Run — API service
######################################################################

variable "api_service_name" {
  type        = string
  description = "Name of the API Cloud Run service."
  default     = "app-api"
}

variable "api_command" {
  type        = list(string)
  description = "Entrypoint command for the API container. Empty uses the image default."
  default     = []
}

variable "api_ingress" {
  type        = string
  description = "Ingress setting for the API service."
  default     = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
}

variable "api_min_instances" {
  type        = number
  description = "Minimum API instances."
  default     = 1
}

variable "api_max_instances" {
  type        = number
  description = "Maximum API instances."
  default     = 10
}

variable "api_cpu" {
  type        = string
  description = "CPU limit for the API container."
  default     = "1"
}

variable "api_memory" {
  type        = string
  description = "Memory limit for the API container."
  default     = "1Gi"
}

variable "api_startup_probe_path" {
  type        = string
  description = "Startup probe HTTP path for the API. Empty disables it."
  default     = "/api/v1/health/live"
}

variable "api_liveness_probe_path" {
  type        = string
  description = "Liveness probe HTTP path for the API. Empty disables it."
  default     = "/api/v1/health/live"
}

######################################################################
# Cloud Run — worker service
######################################################################

variable "worker_service_name" {
  type        = string
  description = "Name of the Celery worker Cloud Run service."
  default     = "app-worker"
}

variable "worker_command" {
  type        = list(string)
  description = "Entrypoint command for the worker container. Empty uses the image default."
  default     = []
}

variable "worker_min_instances" {
  type        = number
  description = "Minimum worker instances (>= 1 for always-on Celery)."
  default     = 1
}

variable "worker_max_instances" {
  type        = number
  description = "Maximum worker instances."
  default     = 3
}

variable "worker_cpu" {
  type        = string
  description = "CPU limit for the worker container."
  default     = "1"
}

variable "worker_memory" {
  type        = string
  description = "Memory limit for the worker container."
  default     = "1Gi"
}

######################################################################
# Cloud Run — beat (scheduler) service
######################################################################

variable "beat_service_name" {
  type        = string
  description = "Name of the Celery beat Cloud Run service."
  default     = "app-beat"
}

variable "beat_command" {
  type        = list(string)
  description = "Entrypoint command for the beat container. Empty uses the image default."
  default     = []
}

variable "beat_min_instances" {
  type        = number
  description = "Minimum beat instances (>= 1 for always-on scheduler)."
  default     = 1
}

variable "beat_max_instances" {
  type        = number
  description = "Maximum beat instances (keep at 1 to avoid double-firing)."
  default     = 1
}

variable "beat_cpu" {
  type        = string
  description = "CPU limit for the beat container."
  default     = "1"
}

variable "beat_memory" {
  type        = string
  description = "Memory limit for the beat container."
  default     = "512Mi"
}

######################################################################
# Cloud Run — migrate job
######################################################################

variable "migrate_job_name" {
  type        = string
  description = "Name of the database migration Cloud Run job."
  default     = "app-migrate"
}

variable "migrate_command" {
  type        = list(string)
  description = "Entrypoint command for the migrate job. Empty uses the image default."
  default     = []
}

variable "migrate_cpu" {
  type        = string
  description = "CPU limit for the migrate job."
  default     = "1"
}

variable "migrate_memory" {
  type        = string
  description = "Memory limit for the migrate job."
  default     = "512Mi"
}

######################################################################
# Shared Cloud Run runtime config
######################################################################

variable "container_port" {
  type        = number
  description = "Container port the HTTP services listen on."
  default     = 8000
}

variable "vpc_egress" {
  type        = string
  description = "Cloud Run VPC egress setting (PRIVATE_RANGES_ONLY or ALL_TRAFFIC)."
  default     = "PRIVATE_RANGES_ONLY"
}

variable "runtime_env" {
  type        = map(string)
  description = "Plain (non-secret) environment variables shared by all Cloud Run workloads."
  default     = {}
}

variable "runtime_secret_env" {
  type = map(object({
    secret  = string
    version = optional(string, "latest")
  }))
  description = "Secret-backed env vars shared by all Cloud Run workloads: env var name => { secret, version }."
  default     = {}
}

######################################################################
# Cloud Build
######################################################################

variable "cloud_build_trigger_name" {
  type        = string
  description = "Name of the Cloud Build trigger."
  default     = "app-deploy"
}

variable "cloud_build_region" {
  type        = string
  description = "Region of the Cloud Build trigger (\"global\" for unregionalized)."
  default     = "global"
}

variable "github_owner" {
  type        = string
  description = "GitHub repository owner (user or org)."
}

variable "github_repo" {
  type        = string
  description = "GitHub repository name."
}

variable "github_branch_regex" {
  type        = string
  description = "Regex matching branches that fire the trigger."
  default     = "^main$"
}

variable "cloud_build_config_filename" {
  type        = string
  description = "Path to the Cloud Build config file in the repository."
  default     = "cloudbuild.yaml"
}

variable "cloud_build_substitutions" {
  type        = map(string)
  description = "Substitution variables passed to the build."
  default     = {}
}

######################################################################
# Load balancer
######################################################################

variable "lb_name_prefix" {
  type        = string
  description = "Prefix applied to every load balancer resource name."
  default     = "app"
}

variable "domain" {
  type        = string
  description = "Public domain served by the load balancer (e.g. api.example.com)."
}

variable "lb_enable_cdn" {
  type        = bool
  description = "Enable Cloud CDN on the load balancer backend."
  default     = false
}
