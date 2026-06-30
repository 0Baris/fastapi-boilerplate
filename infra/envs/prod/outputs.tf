######################################################################
# Load balancer
######################################################################

output "lb_ip" {
  description = "Anycast IPv4 of the HTTPS load balancer. Point the domain's A record here."
  value       = module.lb_serverless_neg.lb_ip
}

output "dns_authorization_record" {
  description = "CNAME record to publish so the managed certificate can validate (name, type, data)."
  value       = module.lb_serverless_neg.dns_authorization_record
}

######################################################################
# Cloud Run
######################################################################

output "api_url" {
  description = "Default URL of the API Cloud Run service."
  value       = module.cloud_run_api.uri
}

output "worker_url" {
  description = "Default URL of the worker Cloud Run service."
  value       = module.cloud_run_worker.uri
}

output "beat_url" {
  description = "Default URL of the beat Cloud Run service."
  value       = module.cloud_run_beat.uri
}

output "migrate_job_name" {
  description = "Name of the migration Cloud Run job."
  value       = module.cloud_run_job.job_name
}

######################################################################
# Data stores
######################################################################

output "db_connection_name" {
  description = "Cloud SQL connection name (project:region:instance)."
  value       = module.cloud_sql.connection_name
}

output "db_private_ip" {
  description = "Cloud SQL private IP address."
  value       = module.cloud_sql.private_ip_address
}

output "redis_host" {
  description = "Memorystore (Redis) private host."
  value       = module.memorystore.host
}

output "redis_port" {
  description = "Memorystore (Redis) port."
  value       = module.memorystore.port
}

######################################################################
# Identity / registry
######################################################################

output "runtime_sa_email" {
  description = "Runtime service account email."
  value       = module.iam.runtime_sa_email
}

output "cicd_sa_email" {
  description = "CI/CD service account email."
  value       = module.iam.cicd_sa_email
}

output "artifact_registry_url" {
  description = "Base URL for pushing/pulling images."
  value       = module.artifact_registry.registry_url
}
