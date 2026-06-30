output "repository_id" {
  description = "The Artifact Registry repository ID."
  value       = google_artifact_registry_repository.this.repository_id
}

output "repository_name" {
  description = "The fully qualified repository name."
  value       = google_artifact_registry_repository.this.name
}

output "registry_url" {
  description = "Base URL for pushing/pulling images (<region>-docker.pkg.dev/<project>/<repo>)."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.this.repository_id}"
}
