output "service_name" {
  description = "The Cloud Run service name."
  value       = google_cloud_run_v2_service.this.name
}

output "uri" {
  description = "The default URL of the Cloud Run service."
  value       = google_cloud_run_v2_service.this.uri
}
