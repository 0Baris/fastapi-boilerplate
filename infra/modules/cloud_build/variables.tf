variable "project_id" {
  type        = string
  description = "GCP project ID that owns the Cloud Build trigger."
}

variable "region" {
  type        = string
  description = "Region for the Cloud Build trigger (use \"global\" for an unregionalized trigger)."
  default     = "global"
}

variable "trigger_name" {
  type        = string
  description = "Name of the Cloud Build trigger."
}

variable "github_owner" {
  type        = string
  description = "GitHub repository owner (user or org)."
}

variable "github_repo" {
  type        = string
  description = "GitHub repository name."
}

variable "branch_regex" {
  type        = string
  description = "Regex matching branches that fire the trigger (e.g. ^main$)."
  default     = "^main$"
}

variable "build_config_filename" {
  type        = string
  description = "Path to the Cloud Build config file in the repository."
  default     = "cloudbuild.yaml"
}

variable "service_account" {
  type        = string
  description = "Fully qualified service account the trigger runs as (projects/<p>/serviceAccounts/<email>)."
}

variable "substitutions" {
  type        = map(string)
  description = "Substitution variables passed to the build."
  default     = {}
}
