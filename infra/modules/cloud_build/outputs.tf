output "trigger_id" {
  description = "The Cloud Build trigger ID."
  value       = google_cloudbuild_trigger.this.trigger_id
}

output "trigger_name" {
  description = "The Cloud Build trigger name."
  value       = google_cloudbuild_trigger.this.name
}
